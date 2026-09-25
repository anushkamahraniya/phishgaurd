"""Train the GPU deep-learning checkers and compare each with the classic model on the same test data.

Run from the backend folder, one model at a time or all:
  .venv\\Scripts\\python -m ml.train_deep messages   # DistilBERT            (~20 min on an RTX 5060)
  .venv\\Scripts\\python -m ml.train_deep links      # character CNN          (~10 min)
  .venv\\Scripts\\python -m ml.train_deep voices     # wav2vec2               (~15 min, needs the full DEEP-VOICE wavs)
  .venv\\Scripts\\python -m ml.train_deep screens    # EfficientNet-B0        (~10 min)
  .venv\\Scripts\\python -m ml.train_deep all

Results are merged into models/check_report.json under "deep_<name>", next to the classic numbers.
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from . import deep
from .train_checkers import KAGGLE, MODELS, SEED, decode_qr, link_split, message_split, qr_split, scores

REPORT = MODELS / "check_report.json"


def seed_all():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)


def save_report(key, rep):
    r = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    r[key] = rep
    REPORT.write_text(json.dumps(r, indent=2, default=float))
    print(key, json.dumps(rep, default=float))


def amp():
    return torch.autocast("cuda", dtype=torch.bfloat16, enabled=deep.DEVICE.type == "cuda")


# ------------------------------------------------------------------ messages
def train_messages(epochs=2, batch=16, lr=3e-5):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    seed_all()
    Xtr, Xte, ytr, yte = message_split(clean=False)
    Xtr, Xva, ytr, yva = train_test_split(Xtr, ytr, test_size=0.05, stratify=ytr, random_state=SEED)
    tok = AutoTokenizer.from_pretrained(deep.MSG_BASE)
    model = AutoModelForSequenceClassification.from_pretrained(deep.MSG_BASE, num_labels=2).to(deep.DEVICE)

    def batches(X, y, shuffle):
        order = np.random.permutation(len(X)) if shuffle else np.arange(len(X))
        X = [deep.prep_message(t) for t in X]
        for i in range(0, len(X), batch):
            idx = order[i:i + batch]
            enc = tok([X[j] for j in idx], truncation=True, max_length=deep.MSG_MAXLEN, padding=True, return_tensors="pt")
            yield enc.to(deep.DEVICE), torch.tensor(y[idx], device=deep.DEVICE)

    @torch.no_grad()
    def predict(X, y):
        model.eval()
        out = []
        for enc, _ in batches(list(X), y, False):
            with amp():
                out.append(torch.softmax(model(**enc).logits.float(), -1)[:, 1].cpu())
        model.train()
        return torch.cat(out).numpy()

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * ((len(Xtr) + batch - 1) // batch)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    best, t = -1, time.time()
    model.train()
    for ep in range(epochs):
        for k, (enc, yb) in enumerate(batches(list(Xtr), ytr, True)):
            with amp():
                loss = nn.functional.cross_entropy(model(**enc).logits.float(), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            if k % 200 == 0:
                print(f"  epoch {ep + 1} step {k} loss {loss.item():.4f} ({time.time() - t:.0f}s)", flush=True)
        va = scores(yva, predict(Xva, yva))
        print(f"  epoch {ep + 1} validation {va}", flush=True)
        if va["roc_auc"] > best:
            best = va["roc_auc"]
            model.save_pretrained(deep.MSG_DIR); tok.save_pretrained(deep.MSG_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(deep.MSG_DIR).to(deep.DEVICE)
    save_report("deep_messages", {"model": "DistilBERT (distilbert-base-uncased) fine-tuned", "n_train": len(Xtr),
                                  "epochs": epochs, "test": scores(yte, predict(Xte, yte)),
                                  "minutes": round((time.time() - t) / 60, 1)})


# --------------------------------------------------------------------- links
def train_links(epochs=4, batch=1024, lr=2e-3):
    seed_all()
    Xtr, Xte, ytr, yte = link_split()
    Xtr, Xva, ytr, yva = train_test_split(list(Xtr), ytr, test_size=0.02, stratify=ytr, random_state=SEED)
    tr = DataLoader(TensorDataset(deep.encode_links(Xtr), torch.tensor(ytr, dtype=torch.float32)), batch_size=batch, shuffle=True)
    model = deep.CharCNN().to(deep.DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * len(tr))

    @torch.no_grad()
    def predict(X):
        model.eval()
        enc = deep.encode_links(list(X))
        out = []
        for i in range(0, len(enc), 4096):
            with amp():
                out.append(torch.sigmoid(model(enc[i:i + 4096].to(deep.DEVICE)).float()).cpu())
        model.train()
        return torch.cat(out).numpy()

    best, t = -1, time.time()
    for ep in range(epochs):
        for xb, yb in tr:
            with amp():
                loss = nn.functional.binary_cross_entropy_with_logits(model(xb.to(deep.DEVICE)).float(), yb.to(deep.DEVICE))
            loss.backward(); opt.step(); sched.step(); opt.zero_grad()
        va = scores(yva, predict(Xva))
        print(f"  epoch {ep + 1} loss {loss.item():.4f} validation {va} ({time.time() - t:.0f}s)", flush=True)
        if va["roc_auc"] > best:
            best = va["roc_auc"]
            torch.save(model.state_dict(), deep.LINK_PATH)
    model.load_state_dict(torch.load(deep.LINK_PATH))
    rows, unread = decode_qr(qr_split()[0])
    rows = [r for r in rows if r[0]]
    from .checkers import normalize_url
    qr = scores(np.array([y for _, y in rows]), predict([normalize_url(u) for u, _ in rows]))
    save_report("deep_links", {"model": "Character CNN (widths 3/5/7, 256 filters each)", "n_train": len(Xtr), "epochs": epochs,
                               "test": scores(yte, predict(Xte)), "qr_test": qr, "minutes": round((time.time() - t) / 60, 1)})


# -------------------------------------------------------------------- voices
VOICE_HOLDOUT = {"taylor", "margot"}  # never trained on: tests whether it works on new people


def _voice_files():
    root = KAGGLE / "deepvoice"
    files = sorted(root.rglob("KAGGLE/AUDIO/*/*.wav"))
    out = []
    for f in files:
        label = int(f.parent.name.upper() == "FAKE")
        people = set(f.stem.lower().replace("-original", "").split("-to-"))
        out.append((f, label, bool(people & VOICE_HOLDOUT)))
    return out


def _load16k(f, seconds=None):
    import librosa
    y, _ = librosa.load(f, sr=deep.VOICE_SR, mono=True, duration=seconds)
    return y


def train_voices(epochs=3, batch=8, lr=3e-5, clips_per_class=2400):
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
    seed_all()
    files = _voice_files()
    if not files:
        raise SystemExit("Voice wavs not found in data/kaggle/deepvoice. Download them first.")
    train = [f for f in files if not f[2]]
    test = [f for f in files if f[2]]
    X, y = [], []
    for label in (0, 1):
        fs = [f for f, lab, _ in train if lab == label]
        per_file = clips_per_class // len(fs) + 1
        for f in fs:
            c = deep.voice_clips(_load16k(f), hop=deep.VOICE_CLIP)
            pick = np.random.permutation(len(c))[:per_file]
            X.append(c[pick]); y += [label] * len(pick)
            print(f"  loaded {f.name}: {len(pick)} clips", flush=True)
    X, y = np.concatenate(X), np.array(y)
    Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.1, stratify=y, random_state=SEED)

    fx = AutoFeatureExtractor.from_pretrained(deep.VOICE_BASE)
    model = AutoModelForAudioClassification.from_pretrained(deep.VOICE_BASE, num_labels=2).to(deep.DEVICE)
    model.freeze_feature_encoder()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)

    @torch.no_grad()
    def predict(clips):
        model.eval()
        out = []
        for i in range(0, len(clips), 16):
            enc = fx(list(clips[i:i + 16]), sampling_rate=deep.VOICE_SR, return_tensors="pt").to(deep.DEVICE)
            with amp():
                out.append(torch.softmax(model(**enc).logits.float(), -1)[:, 1].cpu())
        model.train()
        return torch.cat(out).numpy()

    best, t = -1, time.time()
    model.train()
    for ep in range(epochs):
        order = np.random.permutation(len(Xtr))
        for k in range(0, len(order), batch):
            idx = order[k:k + batch]
            enc = fx(list(Xtr[idx]), sampling_rate=deep.VOICE_SR, return_tensors="pt").to(deep.DEVICE)
            with amp():
                loss = nn.functional.cross_entropy(model(**enc).logits.float(), torch.tensor(ytr[idx], device=deep.DEVICE))
            loss.backward(); opt.step(); opt.zero_grad()
        va = scores(yva, predict(Xva))
        print(f"  epoch {ep + 1} loss {loss.item():.4f} validation {va} ({time.time() - t:.0f}s)", flush=True)
        if va["roc_auc"] > best:
            best = va["roc_auc"]
            model.save_pretrained(deep.VOICE_DIR); fx.save_pretrained(deep.VOICE_DIR)
    model = AutoModelForAudioClassification.from_pretrained(deep.VOICE_DIR).to(deep.DEVICE)

    # New-speaker test: first 2 minutes of every held-out file, scored by both models.
    classic = joblib.load(MODELS / "check_voices.joblib")
    from .checkers import VOICE_SR as CLASSIC_SR, voice_windows
    import librosa
    dy, dp, cy, cp = [], [], [], []
    for f, label, _ in test:
        y16 = _load16k(f, 120)
        p = predict(deep.voice_clips(y16)); dp += list(p); dy += [label] * len(p)
        w = voice_windows(librosa.load(f, sr=CLASSIC_SR, mono=True, duration=120)[0])
        if len(w):
            q = classic.predict_proba(w)[:, 1]; cp += list(q); cy += [label] * len(q)
    save_report("deep_voices", {
        "model": "wav2vec2-base fine-tuned on 2-second clips", "n_train": int(len(Xtr)), "epochs": epochs,
        "validation": scores(yva, predict(Xva)),
        "new_speaker_test": {"speakers": sorted(VOICE_HOLDOUT), "files": len(test), "deep": scores(np.array(dy), np.array(dp)),
                             "classic": scores(np.array(cy), np.array(cp)),
                             "note": "The classic model was trained on the Kaggle CSV, which includes these speakers."},
        "minutes": round((time.time() - t) / 60, 1)})


# ------------------------------------------------------------------- screens
def _screen_files():
    import hashlib
    root = KAGGLE / "screens"
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    out, seen = [], set()
    for f in sorted(root.rglob("*")):
        if f.suffix.lower() not in exts:
            continue
        p = str(f.relative_to(root)).lower()
        if "waste" in p:
            continue  # the dataset author's rejected screenshots
        label = 1 if "phish" in p else 0 if ("legit" in p or "genuine" in p) else None
        digest = hashlib.md5(f.read_bytes()).hexdigest()
        if label is None or digest in seen:
            continue  # exact duplicates would leak between train and test
        seen.add(digest)
        out.append((f, label))
    return out


class _Screens(torch.utils.data.Dataset):
    def __init__(self, items, train):
        self.items, self.tf = items, deep.screen_transform(train)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        from PIL import Image
        f, y = self.items[i]
        with Image.open(f) as im:
            return self.tf(im.convert("RGB")), torch.tensor(y, dtype=torch.float32)


def train_screens(epochs=6, batch=32, lr=3e-4):
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0
    seed_all()
    items = _screen_files()
    if not items:
        raise SystemExit("Screenshots not found in data/kaggle/screens. Download them first.")
    ys = [y for _, y in items]
    tr, te = train_test_split(items, test_size=0.15, stratify=ys, random_state=SEED)
    tr, va = train_test_split(tr, test_size=0.12, stratify=[y for _, y in tr], random_state=SEED)
    print(f"  screenshots: {len(tr)} train, {len(va)} validation, {len(te)} test; phishing share {np.mean(ys):.2f}", flush=True)
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 1)
    model = model.to(deep.DEVICE)
    load = lambda d, train: DataLoader(_Screens(d, train), batch_size=batch, shuffle=train, num_workers=0)
    trl = load(tr, True)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * len(trl))

    @torch.no_grad()
    def predict(d):
        model.eval()
        out, ys = [], []
        for xb, yb in load(d, False):
            with amp():
                out.append(torch.sigmoid(model(xb.to(deep.DEVICE)).float().squeeze(1)).cpu())
            ys.append(yb)
        model.train()
        return torch.cat(ys).numpy().astype(int), torch.cat(out).numpy()

    best, t = -1, time.time()
    for ep in range(epochs):
        for xb, yb in trl:
            with amp():
                loss = nn.functional.binary_cross_entropy_with_logits(model(xb.to(deep.DEVICE)).float().squeeze(1), yb.to(deep.DEVICE))
            loss.backward(); opt.step(); sched.step(); opt.zero_grad()
        va_scores = scores(*predict(va))
        print(f"  epoch {ep + 1} loss {loss.item():.4f} validation {va_scores} ({time.time() - t:.0f}s)", flush=True)
        if va_scores["roc_auc"] > best:
            best = va_scores["roc_auc"]
            torch.save(model.state_dict(), deep.SCREEN_PATH)
    model.load_state_dict(torch.load(deep.SCREEN_PATH))
    save_report("deep_screens", {"model": "EfficientNet-B0 (ImageNet) fine-tuned", "dataset": "Kaggle rohithreddyt/phishing-and-legit-website-screenshots-dataset",
                                 "n_train": len(tr), "epochs": epochs, "test": scores(*predict(te)),
                                 "minutes": round((time.time() - t) / 60, 1)})


# ----------------------------------------------------------------------- OCR
def test_ocr():
    """Phone screenshots of real spam texts (Kaggle tapakah68/spam-text-messages-dataset) come with the true
    text, so we can measure how much of each message the screenshot reader recovers."""
    import difflib
    import re
    import pandas as pd
    from app.checker import Checker
    root = KAGGLE / "sms_images"
    truth = pd.read_csv(root / "spam_texts.csv")
    c = Checker()
    words = lambda t: re.findall(r"[a-z0-9]+", str(t).lower())
    recall, verdicts = [], {"fraud": 0, "careful": 0, "safe": 0, "unknown": 0}
    for _, row in truth.iterrows():
        read = c.deep.read_text((root / row.image).read_bytes())
        want, got = words(row.text), set(words(read))
        recall.append(sum(w in got for w in want) / max(1, len(want)))
        verdicts[c.check_message(read)["verdict"] if len(read) >= 15 else "unknown"] += 1
    save_report("ocr_sms_screens", {"reader": "EasyOCR (English)", "dataset": "Kaggle tapakah68/spam-text-messages-dataset",
                                    "images": len(truth), "words_recovered": round(float(np.mean(recall)), 4),
                                    "verdicts": verdicts,
                                    "note": "These are marketing spam, not all scams, so verdicts are shown but not scored."})


if __name__ == "__main__":
    jobs = {"messages": train_messages, "links": train_links, "voices": train_voices, "screens": train_screens, "ocr": test_ocr}
    names = sys.argv[1:] or ["all"]
    for name in (list(jobs) if names == ["all"] else names):
        print(f"== {name} on {deep.DEVICE}", flush=True)
        jobs[name]()
