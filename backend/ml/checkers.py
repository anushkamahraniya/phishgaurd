"""Shared feature code for the "Check a message" tools (links, messages, QR images, voices).

Used both by ml.train_checkers (training on Kaggle data) and app.checker (live checks),
so training and inference always compute features the same way.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

import numpy as np

# ------------------------------------------------------------------- links
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>\"']*)?", re.I)

BRANDS = ["paypal", "microsoft", "office365", "outlook", "apple", "icloud", "google", "gmail", "amazon",
          "netflix", "facebook", "instagram", "whatsapp", "bank", "chase", "wellsfargo", "hsbc", "dhl",
          "fedex", "ups", "irs", "hmrc", "linkedin", "dropbox", "docusign", "adobe", "sbi", "hdfc", "icici"]
LOOKALIKE = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
BAIT = ["login", "log-in", "signin", "sign-in", "verify", "verification", "secure", "account", "update",
        "confirm", "password", "banking", "wallet", "suspend", "unlock", "billing", "invoice", "reset"]
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "cutt.ly", "rb.gy", "shorturl.at", "tiny.cc"}
RISKY_TLDS = {"zip", "mov", "xyz", "top", "tk", "ml", "ga", "cf", "gq", "buzz", "click", "country", "kim", "work", "rest", "cam"}


def normalize_url(u: str) -> str:
    """Strip scheme and "www." so the model can't just learn which sources wrote "http://" (a known
    quirk of the Kaggle data, where most safe URLs have no scheme)."""
    u = u.strip().strip("<>\"'").lower()
    u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", u)
    return re.sub(r"^www\d?\.", "", u)


def url_host(u: str) -> str:
    u = u.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", u, re.I):
        u = "http://" + u
    try:
        return (urlsplit(u).hostname or "").lower()
    except ValueError:
        return ""


def registered_domain(host: str) -> str:
    parts = host.split(".")
    # Good enough for reasons text: handles co.uk / com.au style endings.
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "org", "net", "gov", "ac", "edu"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def link_reasons(url: str) -> list[str]:
    """Plain-English red flags a person can check themselves."""
    raw = url.strip()
    host = url_host(raw)
    low = raw.lower()
    reasons = []
    try:
        ipaddress.ip_address(host)
        reasons.append("Uses a number address instead of a website name")
    except ValueError:
        pass
    if "@" in low.split("?")[0] and "://" in low:
        reasons.append("Has an “@” that hides the real website")
    dom = registered_domain(host)
    name = dom.split(".")[0] if dom else ""
    plain_host = host.translate(LOOKALIKE)
    for b in BRANDS:
        if b in plain_host and b not in name:
            reasons.append(f"Pretends to be {b.capitalize()} but the real website is {dom}")
            break
        if b in plain_host and b in name and b not in host:
            reasons.append(f"Swaps letters for numbers to look like {b.capitalize()}")
            break
        if b in name and name != b and len(b) > 3:
            reasons.append(f"Uses the name {b.capitalize()} but isn’t {b.capitalize()}’s real website")
            break
    if host in SHORTENERS:
        reasons.append("Short link that hides where it really goes")
    if host.count(".") >= 4:
        reasons.append("Very long, confusing website name")
    if host.rsplit(".", 1)[-1] in RISKY_TLDS:
        reasons.append(f"Ends in “.{host.rsplit('.', 1)[-1]}”, often used by scammers")
    bait = [w for w in BAIT if w in low]
    if bait:
        reasons.append(f"Uses bait words like “{bait[0]}”")
    if low.startswith("http://"):
        reasons.append("Not a secure (https) link")
    if host.count("-") >= 3:
        reasons.append("Lots of dashes in the website name")
    return reasons


# ---------------------------------------------------------------- messages
MSG_FLAGS = [
    (r"\b(urgent|immediately|right away|within \d+ ?(hours?|hrs?|minutes?)|today only|act now|final notice|expires?)\b",
     "Rushes you to act fast"),
    (r"\b(send|share|enter|give|tell|reply with|provide|confirm|read out|type)\b(?:\W+\w+){0,4}?\W+"
     r"(password|passcode|pin|otp|one[- ]time code|security code|login details|credentials|code)\b",
     "Asks for a password or code"),
    (r"\b(bank details|account number|card number|credit card|debit card|cvv|ssn|social security)\b",
     "Asks for bank or card details"),
    (r"\b(gift ?cards?|bitcoin|crypto|wire transfer|western union|money ?gram)\b", "Asks for gift cards, crypto or a transfer"),
    (r"\b(won|winner|prize|lottery|reward|free money|cash prize|inheritance|million)\b", "Promises a prize or free money"),
    (r"\b(suspended|locked|blocked|unusual activity|unauthori[sz]ed|compromised|deactivat)", "Says your account is in trouble"),
    (r"\b(verify|confirm|update) (your|the)? ?(account|identity|details|information)\b", "Asks you to confirm your details"),
    (r"\b(click (here|below|the link)|open the attachment|download)\b", "Pushes you to click or download"),
    (r"\b(dear (customer|user|client|member|applicant|sir|madam)|valued customer)\b", "Doesn’t use your name"),
]


NEGATION = re.compile(r"\b(do not|don't|dont|never|won't|will not|no one|nobody)\b(?:\W+\w+){0,3}?\W*$")


def message_reasons(text: str) -> list[str]:
    """Red flags in a message. A warning like "never share your code" is not itself a red flag."""
    low = text.lower()
    out = []
    for pat, label in MSG_FLAGS:
        m = re.search(pat, low)
        if m and not NEGATION.search(low[max(0, m.start() - 30):m.start()]):
            out.append(label)
    return out


def clean_message(text: str) -> str:
    """Lower-case and space out punctuation, matching the style of the Kaggle email text."""
    t = text.lower()
    t = URL_RE.sub(" linktoken ", t)
    t = re.sub(r"([.,!?;:()\"$%/])", r" \1 ", t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------- voice
VOICE_SR = 44100
VOICE_COLS = ["chroma_stft", "rms", "spectral_centroid", "spectral_bandwidth", "rolloff", "zero_crossing_rate",
              *[f"mfcc{i}" for i in range(1, 21)]]


def voice_windows(y: np.ndarray, sr: int = VOICE_SR) -> np.ndarray:
    """One row of DEEP-VOICE style features per 1-second window (same recipe as the Kaggle CSV)."""
    import librosa
    rows = []
    for s in range(0, len(y) - sr + 1, sr):
        w = y[s:s + sr]
        if float(np.sqrt(np.mean(w ** 2))) < 1e-3:
            continue  # skip silence
        mf = librosa.feature.mfcc(y=w, sr=sr, n_mfcc=20).mean(axis=1)
        rows.append([librosa.feature.chroma_stft(y=w, sr=sr).mean(), librosa.feature.rms(y=w).mean(),
                     librosa.feature.spectral_centroid(y=w, sr=sr).mean(),
                     librosa.feature.spectral_bandwidth(y=w, sr=sr).mean(),
                     librosa.feature.spectral_rolloff(y=w, sr=sr).mean(),
                     librosa.feature.zero_crossing_rate(w).mean(), *mf])
    return np.asarray(rows, dtype=float)


# ---------------------------------------------------------------------- QR
def first_url(text: str) -> str | None:
    """The first link inside some text, without trailing punctuation or a cut-off "..."."""
    m = URL_RE.search(text)
    return re.sub(r"(\.\.\.|…)$", "", m.group(0)).rstrip(".,;)") if m else None


def read_qr(image_bytes: bytes) -> str | None:
    """Return the text inside a QR code picture, or None if no QR code can be read."""
    import cv2
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    det = cv2.QRCodeDetector()
    for candidate in (img, cv2.copyMakeBorder(img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))):
        text, _, _ = det.detectAndDecode(candidate)
        if text:
            return text
    return None
