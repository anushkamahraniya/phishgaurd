"""Train the "Check a message" models on real Kaggle data and write them to backend/models/.

Datasets (downloaded into backend/data/kaggle/ with the Kaggle CLI):
  links     sid321axn/malicious-urls-dataset          malicious_phish.csv
  messages  subhajournal/phishingemails               Phishing_Email.csv
            uciml/sms-spam-collection-dataset         spam.csv (short text messages)
  voices    birdy654/deep-voice-deepfake-voice-recognition   DATASET-balanced.csv
  QR images samahsadiq/benign-and-malicious-qr-codes  (used to test the QR check end to end)

Run from the backend folder:  .venv\\Scripts\\python -m ml.train_checkers
"""
from __future__ import annotations

import json
import random
import time
import zipfile
from multiprocessing import Pool
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from .checkers import VOICE_COLS, clean_message, first_url, normalize_url, read_qr

ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ROOT / "data" / "kaggle"
MODELS = ROOT / "models"
SEED = 7
QR_TEST_PER_CLASS = 1000
QR_TRAIN_PER_CLASS = 20_000
_zip = None


def qr_zip():
    zips = list(KAGGLE.glob("benign-and-malicious-qr-codes*.zip"))
    return zips[0] if zips else None


def qr_split():
    """Fixed test images (never trained on) and a separate pool of training images, per class."""
    with zipfile.ZipFile(qr_zip()) as z:
        names = sorted(x for x in z.namelist() if x.lower().endswith(".png"))
    rng = random.Random(SEED)
    test, train = [], []
    for lab in ("benign", "malicious"):
        files = [x for x in names if f"/{lab}/" in x.lower()]
        rng.shuffle(files)
        test += [(f, lab) for f in files[:QR_TEST_PER_CLASS]]
        train += [(f, lab) for f in files[QR_TEST_PER_CLASS:QR_TEST_PER_CLASS + QR_TRAIN_PER_CLASS]]
    return test, train


def _open_zip():
    global _zip
    _zip = zipfile.ZipFile(qr_zip())


def _decode(name):
    t = read_qr(_zip.read(name))
    return t and first_url(t)  # these codes wrap the link in stray table text


def decode_qr(items):
    with Pool(initializer=_open_zip) as pool:
        urls = pool.map(_decode, [f for f, _ in items], chunksize=200)
    return [(u, int(lab == "malicious")) for u, (_, lab) in zip(urls, items)], sum(u is None for u in urls)


def qr_training_links():
    """Links read out of the Kaggle QR images, cached to CSV because decoding 40k images takes a while."""
    cache = KAGGLE / "qr_links_train.csv"
    if cache.exists():
        return pd.read_csv(cache)
    if not qr_zip():
        return pd.DataFrame(columns=["url", "y"])
    rows, _ = decode_qr(qr_split()[1])
    df = pd.DataFrame([r for r in rows if r[0]], columns=["url", "y"])
    df.to_csv(cache, index=False)
    return df


def scores(y, p):
    pred = (p >= 0.5).astype(int)
    return {"n_test": int(len(y)), "accuracy": round(accuracy_score(y, pred), 4),
            "precision": round(precision_score(y, pred), 4), "recall": round(recall_score(y, pred), 4),
            "roc_auc": round(roc_auc_score(y, p), 4)}


def link_split():
    """Train/test split shared by the classic and deep link models."""
    df = pd.read_csv(KAGGLE / "malicious_phish.csv").dropna()
    X = df.url.map(normalize_url)
    y = (df.type != "benign").astype(int).values  # phishing, malware and hacked sites all count as unsafe
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    qr = qr_training_links()  # links from QR images come from other websites, which helps it generalise
    Xtr = pd.concat([Xtr, qr.url.map(normalize_url)], ignore_index=True)
    return Xtr, Xte.reset_index(drop=True), np.concatenate([ytr, qr.y.values]), yte


def message_split(clean=True):
    """Train/test split shared by the classic and deep message models."""
    em = pd.read_csv(KAGGLE / "Phishing_Email.csv").dropna(subset=["Email Text"])
    em = pd.DataFrame({"text": em["Email Text"], "y": (em["Email Type"] == "Phishing Email").astype(int), "src": "email"})
    sms = pd.read_csv(KAGGLE / "spam.csv", encoding="latin-1")
    sms = pd.DataFrame({"text": sms.v2, "y": (sms.v1 == "spam").astype(int), "src": "sms"})
    df = pd.concat([em, sms], ignore_index=True)
    df = df[df.text.str.strip().str.len() > 0]
    X = df.text.map(clean_message) if clean else df.text
    return train_test_split(X, df.y.values, test_size=0.2, stratify=df.y.values, random_state=SEED)


def train_links():
    Xtr, Xte, ytr, yte = link_split()
    model = make_pipeline(
        TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=3, max_features=300_000, sublinear_tf=True, dtype=np.float32),
        LogisticRegression(C=4, max_iter=2000, solver="liblinear"))
    model.fit(Xtr, ytr)
    rep = {"dataset": "Kaggle sid321axn/malicious-urls-dataset + links read from QR images", "n_train": int(len(Xtr)), "test": scores(yte, model.predict_proba(Xte)[:, 1])}
    return model, rep


def train_messages():
    Xtr, Xte, ytr, yte = message_split()
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=150_000, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b"),
        LogisticRegression(C=8, max_iter=2000, solver="liblinear"))
    model.fit(Xtr, ytr)
    rep = {"dataset": "Kaggle subhajournal/phishingemails + uciml/sms-spam-collection-dataset", "n_train": int(len(Xtr)), "test": scores(yte, model.predict_proba(Xte)[:, 1])}
    return model, rep


def train_voices():
    df = pd.read_csv(KAGGLE / "DATASET-balanced.csv")
    X = df[VOICE_COLS].values
    y = (df.LABEL == "FAKE").astype(int).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    model = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.08, random_state=SEED)
    model.fit(Xtr, ytr)
    rep = {"dataset": "Kaggle birdy654/deep-voice-deepfake-voice-recognition", "n_train": int(len(Xtr)),
           "test": scores(yte, model.predict_proba(Xte)[:, 1]),
           "note": "1-second windows from 8 public speakers; random split, so real-world accuracy will be lower."}
    return model, rep


def test_qr(link_model):
    """End-to-end QR check on held-out Kaggle QR images: read the code, then score the link inside."""
    if not qr_zip():
        return {"skipped": "QR dataset zip not found"}
    items = qr_split()[0]
    rows, unread = decode_qr(items)
    rows = [r for r in rows if r[0]]
    p = link_model.predict_proba([normalize_url(u) for u, _ in rows])[:, 1]
    return {"dataset": "Kaggle samahsadiq/benign-and-malicious-qr-codes", "images_tried": len(items),
            "read_ok": round(1 - unread / len(items), 4), "test": scores(np.array([y for _, y in rows]), p)}


def main():
    MODELS.mkdir(exist_ok=True)
    report = {}
    for name, fn in [("links", train_links), ("messages", train_messages), ("voices", train_voices)]:
        t = time.time()
        model, rep = fn()
        joblib.dump(model, MODELS / f"check_{name}.joblib", compress=3)
        report[name] = rep
        print(f"{name:9s} {rep['test']}  ({time.time() - t:.0f}s)")
        if name == "links":
            report["qr"] = test_qr(model)
            print(f"qr        {report['qr']}")
    (MODELS / "check_report.json").write_text(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
