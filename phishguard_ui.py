"""Shared helpers for the Streamlit pages: cached models plus plain-English wording."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BACKEND = Path(__file__).resolve().parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.checker import get_checker  # noqa: E402
from app.engine import get_engine  # noqa: E402


@st.cache_resource(show_spinner="Loading employee data…")
def engine():
    return get_engine()


@st.cache_resource(show_spinner="Loading the scam checkers…")
def checker():
    return get_checker()


# ------------------------------------------------------------------ wording
LEVEL = {"High": ("High risk", "red"), "Medium": ("Watch", "orange"), "Low": ("Safe", "green")}
MOD = {"text": "Emails", "image": "Images & QR codes", "url": "Links", "audio": "Phone calls"}
ONE = {"text": "email", "image": "QR code", "url": "link", "audio": "phone call"}

COURSES = {
    "URL Typosquatting & SSL Spoofing": "Spotting fake links",
    "Urgency & Pretext Email Scams": "Spotting scam emails",
    "QR Code & Visual Brand Spoofing": "Fake QR codes and images",
    "Deepfake Voice & Vishing Defense": "Scam phone calls",
    "Pause Before You Click": "Pause before you click",
    "Report It: Using the Phish Alert Button": "How to report phishing",
    "Security Awareness Refresher": "Security refresher",
    "Set Up Multi-Factor Authentication": "Turn on two-step login",
}

REASONS = {
    "url_fail_rate": ("Clicks fake links", "Spots fake links", "%"),
    "text_fail_rate": ("Falls for scam emails", "Spots scam emails", "%"),
    "image_fail_rate": ("Trusts fake images and QR codes", "Spots fake images and QR codes", "%"),
    "audio_fail_rate": ("Trusts scam phone calls", "Spots scam phone calls", "%"),
    "avg_response_sec": ("Clicks very quickly", "Takes time before clicking", "s"),
    "report_rate": ("Rarely reports suspicious messages", "Reports suspicious messages", "%r"),
    "training_completed": ("Has done little training", "Has done training", "n"),
    "days_since_training": ("Training is out of date", "Trained recently", "d"),
    "mfa_enabled": ("No two-step login", "Uses two-step login", ""),
    "after_hours_pct": ("Often reads mail late at night", "Reads mail in work hours", "%h"),
    "seniority": ("Senior role, a bigger target", "Junior role, a smaller target", ""),
    "tenure_years": ("New to the company", "Long time at the company", "y"),
}


def pct(v: float) -> int:
    return int(v)  # floor: 99.9 should read as 99, not a misleading 100


def level_of(v: float) -> str:
    return "High" if v >= 60 else "Medium" if v >= 30 else "Low"


def risk_badge(risk: float, level: str | None = None):
    label, color = LEVEL[level or level_of(risk)]
    st.badge(f"{label} · {pct(risk)}%", color=color)


def course(name: str) -> str:
    return COURSES.get(name, name)


def reason(c: dict) -> tuple[str, str, bool]:
    bad, good, unit = REASONS.get(c["feature"], (c["label"], c["label"], ""))
    v = round(c["value"])
    detail = {"%": f"fell for {v}% of tests", "s": f"in {v} seconds on average", "%r": f"reports {v}% of them",
              "n": f"{v} course{'' if v == 1 else 's'} done", "d": f"{v} days ago", "%h": f"{v}% after hours",
              "y": f"{round(c['value'], 1)} years"}.get(unit, "")
    up = c["shap"] > 0
    return (bad if up else good), detail, up


def plan_step(change: str) -> str:
    if change.startswith("Complete"):
        return "Finish one training course"
    if change.startswith("Report"):
        return "Report more suspicious messages"
    if change.startswith("Take"):
        return "Slow down before clicking"
    if change.startswith("Enable MFA"):
        return "Turn on two-step login"
    if change.startswith("Halve the "):
        what = {"Text": "emails", "Image": "QR codes", "URL": "links", "Audio": "calls"}.get(change.split()[2], "messages")
        return f"Fall for half as many fake {what}"
    return change


# ----------------------------------------------------------- person picker
def person_picker(label="Person", key="picker"):
    """Searchable name list bound to st.session_state.emp_id (shared by every page)."""
    df = engine().df
    ids = df.id.tolist()
    names = dict(zip(df.id, df.name + " · " + df.dept))
    current = st.session_state.get("emp_id", ids[0])
    picked = st.selectbox(label, ids, index=ids.index(current) if current in ids else 0,
                          format_func=names.get, key=key, placeholder="Type a name…")
    st.session_state.emp_id = picked
    return picked


def go(page: str, emp_id: str | None = None):
    if emp_id:
        st.session_state.emp_id = emp_id
    st.switch_page(page)
