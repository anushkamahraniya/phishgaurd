"""Live "Check a message" service: links, messages, QR pictures and voice recordings.

Every answer is {verdict, title, kind, reasons}. verdict is "fraud", "careful" or "safe";
reasons are short plain-English lines for the person checking.
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from ml.checkers import (URL_RE, VOICE_SR, clean_message, first_url, link_reasons, message_reasons, normalize_url,
                         read_qr, registered_domain, url_host, voice_windows)

MODELS = Path(__file__).resolve().parents[1] / "models"
FRAUD, CAREFUL = 0.7, 0.4
MAX_VOICE_SEC = 30
VOICE_ENABLED = False  # voice checks are switched off for now; the code stays for later

# Big, well-known sites. The URL data has few bare homepages, so don't let the model second-guess these.
KNOWN_SAFE = {"google.com", "youtube.com", "microsoft.com", "office.com", "live.com", "apple.com", "amazon.com",
              "amazon.in", "wikipedia.org", "github.com", "linkedin.com", "facebook.com", "instagram.com",
              "paypal.com", "netflix.com", "gov.uk", "gov.in", "bbc.co.uk", "kaggle.com", "claude.ai", "anthropic.com"}


def _verdict(p: float) -> str:
    return "fraud" if p >= FRAUD else "careful" if p >= CAREFUL else "safe"


TITLES = {
    "link": {"fraud": "This link looks like a scam", "careful": "Be careful with this link", "safe": "This link looks safe"},
    "message": {"fraud": "This message looks like a scam", "careful": "Be careful with this message", "safe": "This message looks safe"},
    "qr": {"fraud": "This QR code leads to a scam", "careful": "Be careful with this QR code", "safe": "This QR code looks safe"},
    "voice": {"fraud": "This voice sounds fake (AI-made)", "careful": "This voice might be fake", "safe": "This sounds like a real person"},
    "screenshot": {"fraud": "This screenshot looks like a scam", "careful": "Be careful with this", "safe": "This screenshot looks safe"},
}


def _deep_wins(report: dict, name: str) -> bool:
    """Use a GPU model only if it beat the classic model on the same test data."""
    d = report.get(f"deep_{name}", {})
    if name == "voices":
        t = d.get("new_speaker_test", {})
        return bool(t) and t["deep"]["roc_auc"] > t["classic"]["roc_auc"]
    if name == "screens":
        return bool(d)  # no classic screenshot model to beat
    return bool(d) and d["test"]["roc_auc"] > report.get(name, {}).get("test", {}).get("roc_auc", 1)


class Checker:
    def __init__(self):
        self.links = joblib.load(MODELS / "check_links.joblib")
        self.messages = joblib.load(MODELS / "check_messages.joblib")
        self.voices = joblib.load(MODELS / "check_voices.joblib")
        self.deep, self.use = None, set()
        try:
            from ml.deep import Deep
            self.deep = Deep()
            report = json.loads((MODELS / "check_report.json").read_text())
            loaded = {"messages": self.deep.msg, "links": self.deep.link, "voices": self.deep.voice, "screens": self.deep.screen}
            self.use = {n for n, m in loaded.items() if m is not None and _deep_wins(report, n)}
        except Exception as e:  # no PyTorch or no trained deep models: classic models only
            logging.warning("Deep models not loaded: %s", e)

    # ----------------------------------------------------------------- links
    def known(self, url: str) -> bool:
        return registered_domain(url_host(url)) in KNOWN_SAFE

    def link_score(self, url: str) -> float:
        if self.known(url):
            return 0.02
        if "links" in self.use:
            return float(self.deep.links([normalize_url(url)])[0])
        return float(self.links.predict_proba([normalize_url(url)])[0, 1])

    def check_link(self, url: str, kind: str = "link") -> dict:
        if self.known(url):
            return {"verdict": "safe", "kind": kind, "title": TITLES[kind]["safe"], "found": url,
                    "reasons": [f"{registered_domain(url_host(url))} is a well-known website"]}
        p = self.link_score(url)
        reasons = link_reasons(url)
        v = _verdict(p)
        if v == "safe" and len(reasons) >= 2:
            v = "careful"  # the model is relaxed but there are clear warning signs
        if v != "safe" and not reasons:
            reasons = ["Looks like scam links we’ve seen before"]
        if v == "safe":
            reasons = ["No warning signs found"] + [f"Still check: {r.lower()}" for r in reasons[:1]]
        return {"verdict": v, "kind": kind, "title": TITLES[kind][v], "reasons": reasons[:3], "found": url}

    # -------------------------------------------------------------- messages
    def _scam_words(self, text: str, n=3) -> list[str]:
        vec, clf = self.messages[0], self.messages[-1]
        x = vec.transform([clean_message(text)])
        names = vec.get_feature_names_out()
        coef = clf.coef_[0]
        w = sorted(((float(v * coef[j]), names[j]) for j, v in zip(x.indices, x.data)), reverse=True)
        useful = lambda t: t != "linktoken" and not all(x in ENGLISH_STOP_WORDS or len(x) < 3 for x in t.split())
        return [t for s, t in w if s > 0.05 and useful(t)][:n]

    def message_score(self, text: str) -> float:
        if "messages" in self.use:
            return self.deep.message(text)
        return float(self.messages.predict_proba([clean_message(text)])[0, 1])

    def check_message(self, text: str) -> dict:
        p = self.message_score(text)
        reasons = message_reasons(text)
        urls = [m.group(0).rstrip(".,)") for m in URL_RE.finditer(text)]
        bad_link = None
        for u in urls[:5]:
            lp = self.link_score(u)
            if lp > p:
                p, bad_link = max(p, lp), u
        v = _verdict(p)
        if v == "safe" and len(reasons) >= 2:
            v = "careful"
        if bad_link and v != "safe":
            reasons.insert(0, f"Contains a risky link: {url_host(bad_link) or bad_link}")
        if v != "safe" and len(reasons) < 2:
            words = self._scam_words(text)
            if words:
                reasons.append("Uses words common in scams: " + ", ".join(f"“{w}”" for w in words))
        if v != "safe" and not reasons:
            reasons = ["Reads like scam messages we’ve seen before"]
        if v == "safe":
            reasons = ["No warning signs found"] + reasons[:1]
        return {"verdict": v, "kind": "message", "title": TITLES["message"][v], "reasons": reasons[:3]}

    def check_text(self, text: str) -> dict:
        t = text.strip()
        if " " not in t and "\n" not in t and URL_RE.fullmatch(t):
            return self.check_link(t)
        return self.check_message(t)

    # ------------------------------------------------------------------ files
    def check_image(self, data: bytes) -> dict:
        found = read_qr(data)
        if not found:
            return self.check_screenshot(data)
        url = first_url(found)
        if url:
            found = url
            r = self.check_link(url, kind="qr")
        else:
            r = self.check_message(found)
            r["kind"], r["title"] = "qr", TITLES["qr"][r["verdict"]]
        r["found"] = found
        r["reasons"] = [f"The QR code opens: {found[:80]}"] + r["reasons"][:2]
        return r

    def check_screenshot(self, data: bytes) -> dict:
        """A picture with no QR code: read its words (OCR) and look at it as a web page."""
        none = {"verdict": "unknown", "kind": "screenshot", "title": "Couldn’t find anything to check",
                "reasons": ["Upload a clear QR code, or a screenshot of a message or website"]}
        if self.deep is None:
            return none
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(data))
        except Exception:
            return none
        text = self.deep.read_text(data)
        # Wide pictures are web pages: the website model judges them, because the message model was trained
        # on emails and texts and reads ordinary page wording ("solutions", "learn more") as spam.
        # Tall pictures are phone screenshots (chats, texts): the message check judges them.
        wide = img.width >= img.height * 0.9
        if wide and "screens" in self.use:
            v = _verdict(self.deep.screen_score(img))
            flags = message_reasons(text)
            if v == "safe" and len(flags) >= 2:
                v = "careful"
            reasons = (["Looks like a fake website or login page"] if v != "safe" else ["Looks like a normal website"]) + flags[:1]
        elif len(text) >= 15:
            msg = self.check_message(text)
            v, reasons = msg["verdict"], msg["reasons"]
        else:
            return none
        if text:
            short = " ".join(text.split())
            reasons.append(f"It says: “{short[:70]}{'…' if len(short) > 70 else ''}”")
        return {"verdict": v, "kind": "screenshot", "title": TITLES["screenshot"][v], "reasons": reasons[:3]}

    def voice_fake_scores(self, data: bytes):
        import librosa
        if "voices" in self.use:
            y, _ = librosa.load(io.BytesIO(data), sr=16000, mono=True, duration=MAX_VOICE_SEC)
            return self.deep.voice_scores(y), 2
        y, _ = librosa.load(io.BytesIO(data), sr=VOICE_SR, mono=True, duration=MAX_VOICE_SEC)
        X = voice_windows(y)
        return (self.voices.predict_proba(X)[:, 1] if len(X) else np.zeros(0)), 1

    def check_audio(self, data: bytes) -> dict:
        try:
            fake, sec = self.voice_fake_scores(data)
        except Exception:
            return {"verdict": "unknown", "kind": "voice", "title": "Couldn’t play this file",
                    "reasons": ["Use a .wav, .mp3, .ogg or .flac recording"]}
        if len(fake) * sec < 2:
            return {"verdict": "unknown", "kind": "voice", "title": "Recording too short",
                    "reasons": ["Use at least 3 seconds of someone speaking"]}
        p = float(np.mean(fake))
        v = _verdict(p)
        n_fake = int((np.asarray(fake) >= 0.5).sum())
        reasons = [f"{n_fake * sec} of {len(fake) * sec} seconds sound computer-made"]
        if v != "safe":
            reasons.append("Don’t act on money or code requests. Hang up and call back on a number you trust")
        return {"verdict": v, "kind": "voice", "title": TITLES["voice"][v], "reasons": reasons}

    def check_file(self, data: bytes, filename: str, content_type: str) -> dict:
        name = (filename or "").lower()
        ctype = (content_type or "").lower()
        if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
            return self.check_image(data)
        if VOICE_ENABLED and (ctype.startswith("audio/") or name.endswith((".wav", ".mp3", ".ogg", ".flac", ".m4a"))):
            return self.check_audio(data)
        return {"verdict": "unknown", "kind": "file", "title": "Can’t check this file",
                "reasons": ["Upload a QR code or a screenshot"]}


_checker: Checker | None = None


def get_checker() -> Checker:
    global _checker
    if _checker is None:
        _checker = Checker()
    return _checker
