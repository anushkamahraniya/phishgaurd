"""GPU deep-learning models for the "Is it a scam?" checks, shared by training (ml.train_deep)
and the live app (app.checker). Everything here is optional: if PyTorch or a model folder is
missing, the app falls back to the classic models in ml.train_checkers.

  messages  DistilBERT fine-tuned on emails + text messages     models/deep_messages/
  links     character-level CNN over the link text               models/deep_links.pt
  voices    wav2vec2 fine-tuned on real vs AI-cloned speech       models/deep_voices/
  screens   EfficientNet-B0 fine-tuned on website screenshots    models/deep_screens.pt
  OCR       EasyOCR reads the words in a screenshot (pretrained, not trained here)
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import torch
from torch import nn

MODELS = Path(__file__).resolve().parents[1] / "models"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if DEVICE.type == "cpu":
    torch.set_num_threads(2)  # each CPU thread adds working memory; small hosts have 2 cores anyway
OCR_MAX_SIDE = 1280

# ------------------------------------------------------------------ messages
MSG_BASE = "distilbert-base-uncased"
MSG_DIR = MODELS / "deep_messages"
MSG_MAXLEN = 256
URL_TOKEN = re.compile(r"(?:https?://|www\.)\S+", re.I)


def prep_message(t: str) -> str:
    return URL_TOKEN.sub(" link ", str(t))


# --------------------------------------------------------------------- links
LINK_PATH = MODELS / "deep_links.pt"
LINK_MAXLEN = 200
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;=%"
CHAR_IDX = {c: i + 2 for i, c in enumerate(CHARS)}  # 0 = padding, 1 = any other character


def encode_links(urls: list[str]) -> torch.Tensor:
    out = np.zeros((len(urls), LINK_MAXLEN), dtype=np.int64)
    for r, u in enumerate(urls):
        ids = [CHAR_IDX.get(c, 1) for c in u[:LINK_MAXLEN]]
        out[r, :len(ids)] = ids
    return torch.from_numpy(out)


class CharCNN(nn.Module):
    """Embeds each character, then 1-D convolutions of width 3/5/7 spot patterns like "0ft", "-login", ".xyz"."""

    def __init__(self, vocab=len(CHARS) + 2, emb=48, filters=256, widths=(3, 5, 7)):
        super().__init__()
        self.emb = nn.Embedding(vocab, emb, padding_idx=0)
        self.convs = nn.ModuleList(nn.Conv1d(emb, filters, w, padding=w // 2) for w in widths)
        self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(filters * len(widths), 256), nn.ReLU(),
                                  nn.Dropout(0.3), nn.Linear(256, 1))

    def forward(self, x):
        mask = (x != 0).unsqueeze(1)
        h = self.emb(x).transpose(1, 2)
        pooled = [torch.relu(c(h)).masked_fill(~mask, -1e4).amax(dim=2) for c in self.convs]
        return self.head(torch.cat(pooled, 1)).squeeze(1)


# -------------------------------------------------------------------- voices
VOICE_BASE = "facebook/wav2vec2-base"
VOICE_DIR = MODELS / "deep_voices"
VOICE_SR = 16000
VOICE_CLIP = 2 * VOICE_SR  # 2-second clips


def voice_clips(y: np.ndarray, hop: int = VOICE_CLIP) -> np.ndarray:
    """Cut 16 kHz mono audio into 2-second clips, dropping silent ones."""
    clips = [y[s:s + VOICE_CLIP] for s in range(0, len(y) - VOICE_CLIP + 1, hop)]
    clips = [c for c in clips if float(np.sqrt(np.mean(c ** 2))) > 1e-3]
    return np.stack(clips).astype(np.float32) if clips else np.zeros((0, VOICE_CLIP), np.float32)


# ------------------------------------------------------------------- screens
SCREEN_PATH = MODELS / "deep_screens.pt"
SCREEN_SIZE = 224


def screen_model():
    from torchvision.models import efficientnet_b0
    m = efficientnet_b0(weights=None)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    return m


def screen_transform(train: bool = False):
    from torchvision import transforms as T
    steps = [T.Resize((SCREEN_SIZE, SCREEN_SIZE))]
    if train:
        steps += [T.ColorJitter(0.2, 0.2, 0.2), T.RandomAffine(0, translate=(0.03, 0.03), scale=(0.95, 1.05))]
    return T.Compose(steps + [T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


# ------------------------------------------------------------ live inference
class Deep:
    """Loads whichever trained deep models exist. Each score method returns P(scam) or None."""

    def __init__(self):
        self.msg = self.link = self.voice = self.screen = self.ocr = None
        if MSG_DIR.exists():
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self.msg_tok = AutoTokenizer.from_pretrained(MSG_DIR)
            self.msg = AutoModelForSequenceClassification.from_pretrained(MSG_DIR).to(DEVICE).eval()
        if LINK_PATH.exists():
            self.link = CharCNN().to(DEVICE).eval()
            self.link.load_state_dict(torch.load(LINK_PATH, map_location=DEVICE))
        if VOICE_DIR.exists():
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
            self.voice_fx = AutoFeatureExtractor.from_pretrained(VOICE_DIR)
            self.voice = AutoModelForAudioClassification.from_pretrained(VOICE_DIR).to(DEVICE).eval()
        if SCREEN_PATH.exists():
            self.screen = screen_model().to(DEVICE).eval()
            self.screen.load_state_dict(torch.load(SCREEN_PATH, map_location=DEVICE))

    @torch.no_grad()
    def message(self, text: str) -> float | None:
        if self.msg is None:
            return None
        enc = self.msg_tok([prep_message(text)], truncation=True, max_length=MSG_MAXLEN, return_tensors="pt").to(DEVICE)
        return float(torch.softmax(self.msg(**enc).logits, -1)[0, 1])

    @torch.no_grad()
    def links(self, normalized_urls: list[str]) -> list[float] | None:
        if self.link is None:
            return None
        return torch.sigmoid(self.link(encode_links(normalized_urls).to(DEVICE))).tolist()

    @torch.no_grad()
    def voice_scores(self, y16k: np.ndarray) -> np.ndarray | None:
        if self.voice is None:
            return None
        clips = voice_clips(y16k)
        if not len(clips):
            return np.zeros(0)
        out = []
        for i in range(0, len(clips), 16):
            enc = self.voice_fx(list(clips[i:i + 16]), sampling_rate=VOICE_SR, return_tensors="pt").to(DEVICE)
            out.append(torch.softmax(self.voice(**enc).logits, -1)[:, 1].cpu().numpy())
        return np.concatenate(out)

    @torch.no_grad()
    def screen_score(self, pil_image) -> float | None:
        if self.screen is None:
            return None
        x = screen_transform()(pil_image.convert("RGB")).unsqueeze(0).to(DEVICE)
        return float(torch.sigmoid(self.screen(x))[0])

    def read_text(self, image_bytes: bytes) -> str:
        """Words in a screenshot, top to bottom (EasyOCR, loaded on first use)."""
        if self.ocr is None:
            import easyocr
            self.ocr = easyocr.Reader(["en"], gpu=DEVICE.type == "cuda", verbose=False)
        # Full-size screenshots (e.g. 2880x1800) push EasyOCR past 2 GB of memory, which gets the
        # app killed on small hosts. 1280 px on the long side still reads normal screen text.
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE))
        lines = self.ocr.readtext(np.asarray(img), detail=0, paragraph=True, canvas_size=OCR_MAX_SIDE, batch_size=1)
        return "\n".join(lines).strip()
