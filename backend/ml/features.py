"""Feature definitions shared by training and inference."""
from __future__ import annotations

import pandas as pd

# (column, human label, unit)
EMP_FEATURES = [
    ("url_fail_rate", "Deceptive URL failure rate", "%"),
    ("text_fail_rate", "Email text failure rate", "%"),
    ("image_fail_rate", "Image / QR failure rate", "%"),
    ("audio_fail_rate", "Voice (vishing) failure rate", "%"),
    ("avg_response_sec", "Average time before clicking", "s"),
    ("report_rate", "Reports suspicious messages", "%"),
    ("training_completed", "Training modules completed", ""),
    ("days_since_training", "Days since last training", "days"),
    ("mfa_enabled", "MFA enabled", "bool"),
    ("after_hours_pct", "Mail opened after hours", "%"),
    ("seniority", "Seniority (0 staff, 1 manager, 2 exec)", ""),
    ("tenure_years", "Tenure", "yrs"),
]
EMP_COLS = [c for c, _, _ in EMP_FEATURES]
EMP_LABELS = {c: l for c, l, _ in EMP_FEATURES}
EMP_UNITS = {c: u for c, _, u in EMP_FEATURES}
MODALITIES = ["text", "image", "url", "audio"]

# Which adaptive module addresses which risk driver (used by XAI-driven assignment).
MODULE_FOR_FEATURE = {
    "url_fail_rate": "URL Typosquatting & SSL Spoofing",
    "text_fail_rate": "Urgency & Pretext Email Scams",
    "image_fail_rate": "QR Code & Visual Brand Spoofing",
    "audio_fail_rate": "Deepfake Voice & Vishing Defense",
    "avg_response_sec": "Pause Before You Click",
    "report_rate": "Report It: Using the Phish Alert Button",
    "training_completed": "Security Awareness Refresher",
    "days_since_training": "Security Awareness Refresher",
    "mfa_enabled": "Set Up Multi-Factor Authentication",
    "after_hours_pct": "Pause Before You Click",
}
MODULE_MODALITY = {
    "URL Typosquatting & SSL Spoofing": "url",
    "Urgency & Pretext Email Scams": "text",
    "QR Code & Visual Brand Spoofing": "image",
    "Deepfake Voice & Vishing Defense": "audio",
}


def employee_matrix(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for m in MODALITIES:
        out[f"{m}_fail_rate"] = (df[f"{m}_fails"] / df[f"{m}_sims"].clip(lower=1) * 100).round(1)
    for c in ["avg_response_sec", "report_rate", "training_completed", "days_since_training",
              "mfa_enabled", "after_hours_pct", "seniority", "tenure_years"]:
        out[c] = df[c].astype(float)
    return out[EMP_COLS]
