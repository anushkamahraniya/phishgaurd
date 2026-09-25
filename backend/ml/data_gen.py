"""Synthetic data generation for PhishGuard ML.

Everything here is generated, not collected: an organisation of 1,248 employees
with a simulated phishing-simulation history, plus labelled corpora for the
two content classifiers (email text and voice-call transcripts).

The employee data is produced from a hidden latent "susceptibility" per person.
The model never sees that latent value - it only sees observable behaviour
(failure rates per modality, response time, reporting habits, training), and
has to learn which behaviours predict a click on the *next* simulation.
"""
from __future__ import annotations

import random
import numpy as np
import pandas as pd

SEED = 7
MODALITIES = ["text", "image", "url", "audio"]

DEPARTMENTS = {
    # name: (headcount, latent mean, modality bias {text,image,url,audio})
    "Finance": (142, 0.75, {"text": 0.2, "image": 0.1, "url": 0.6, "audio": 0.2}),
    "Human Resources": (68, 0.45, {"text": 0.6, "image": 0.0, "url": 0.1, "audio": 0.1}),
    "Marketing": (210, 0.30, {"text": 0.0, "image": 0.6, "url": 0.2, "audio": -0.1}),
    "Customer Support": (250, 0.35, {"text": 0.4, "image": 0.0, "url": 0.1, "audio": 0.4}),
    "Legal": (80, 0.15, {"text": 0.2, "image": -0.1, "url": 0.0, "audio": 0.2}),
    "Engineering": (380, -0.45, {"text": -0.3, "image": -0.2, "url": -0.3, "audio": 0.5}),
    "IT Operations": (118, -0.85, {"text": -0.4, "image": -0.3, "url": -0.4, "audio": 0.3}),
}
MODALITY_BASE = {"text": -1.0, "image": -0.75, "url": -0.35, "audio": -1.35}

FIRST = ["Aarav", "Aisha", "Alejandro", "Amelia", "Anika", "Ben", "Camila", "Chloe", "Daniel", "Diego",
         "Elif", "Emma", "Ethan", "Fatima", "Felix", "Grace", "Hana", "Hugo", "Ines", "Isaac", "Jana",
         "Jonas", "Kai", "Kavya", "Leila", "Liam", "Lina", "Luca", "Maya", "Mateo", "Mei", "Mia",
         "Nadia", "Noah", "Nora", "Omar", "Oscar", "Priya", "Rahul", "Rosa", "Sam", "Sara", "Sofia",
         "Tariq", "Theo", "Uma", "Victor", "Yara", "Yusuf", "Zoe"]
LAST = ["Adeyemi", "Andersen", "Bauer", "Bianchi", "Brooks", "Castillo", "Chen", "Costa", "Dubois",
        "Eriksen", "Fischer", "Garcia", "Gupta", "Haddad", "Hughes", "Ivanova", "Jensen", "Kaur",
        "Kim", "Kowalski", "Larsen", "Lopez", "Mahraniya", "Mensah", "Moreau", "Murphy", "Nakamura",
        "Nguyen", "Novak", "Okafor", "Olsen", "Patel", "Petrov", "Quinn", "Rossi", "Sato", "Schmidt",
        "Silva", "Singh", "Suzuki", "Tanaka", "Torres", "Varga", "Wagner", "Walsh", "Weber", "Yilmaz",
        "Young", "Zhang", "Zimmer"]

# The seven people from the original prototype keep their names and profiles.
SHOWCASE = [
    ("Alexander Wright", "Finance", dict(text=70, image=82, url=95, audio=40), 14, 5, 0),
    ("Sophia Chen", "Human Resources", dict(text=89, image=45, url=60, audio=30), 22, 12, 2),
    ("Marcus Brody", "Engineering", dict(text=20, image=15, url=25, audio=65), 180, 55, 3),
    ("Elena Rostova", "Marketing", dict(text=40, image=88, url=50, audio=20), 45, 18, 1),
    ("David Miller", "Finance", dict(text=85, image=90, url=98, audio=70), 8, 2, 0),
    ("Priya Sharma", "Customer Support", dict(text=65, image=30, url=40, audio=15), 90, 30, 2),
    ("Lucas Vance", "IT Operations", dict(text=10, image=12, url=15, audio=35), 340, 82, 5),
]


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate_employees(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pyrng = random.Random(seed)
    rows = []
    used_names = {s[0] for s in SHOWCASE}
    idx = 101
    for dept, (count, mu, bias) in DEPARTMENTS.items():
        for _ in range(count):
            z = rng.normal(mu, 1.0)  # hidden susceptibility
            seniority = rng.choice([0, 1, 2], p=[0.72, 0.22, 0.06])
            tenure = float(np.clip(rng.exponential(4.0), 0.1, 30))
            training = int(np.clip(rng.poisson(np.clip(2.2 - 0.6 * z, 0.2, 5)), 0, 8))
            days_since = int(np.clip(rng.exponential(max(30.0, 120 + 40 * z)), 3, 540)) if training else 540
            mfa = int(rng.random() < _sigmoid(1.2 - 0.6 * z))
            after_hours = float(np.clip(rng.normal(22 + 6 * z, 9), 0, 80))
            rec = {}
            for m in MODALITIES:
                sims = int(rng.poisson(4) + 2)
                p = _sigmoid(z + bias[m] + MODALITY_BASE[m] - 0.18 * training + rng.normal(0, 0.35))
                fails = int(rng.binomial(sims, p))
                rec[f"{m}_sims"] = sims
                rec[f"{m}_fails"] = fails
            resp = float(np.clip(np.exp(rng.normal(4.1 - 0.55 * z, 0.45)), 4, 900))
            report_rate = float(np.clip(_sigmoid(-0.9 * z + 0.25 * training - 0.4 + rng.normal(0, 0.5)) * 100, 0, 100))
            while True:
                name = f"{pyrng.choice(FIRST)} {pyrng.choice(LAST)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            rows.append(dict(
                id=f"EMP-{idx}", name=name, dept=dept, seniority=int(seniority), tenure_years=round(tenure, 1),
                training_completed=training, days_since_training=days_since, mfa_enabled=mfa,
                after_hours_pct=round(after_hours, 1), avg_response_sec=round(resp, 1),
                report_rate=round(report_rate, 1), _z=z, **rec,
            ))
            idx += 1
    df = pd.DataFrame(rows)

    # Drop the showcase people into the first slot of their department.
    for name, dept, rates, resp, report, training in SHOWCASE:
        i = df.index[(df.dept == dept) & (~df.name.isin([s[0] for s in SHOWCASE]))][0]
        df.at[i, "name"] = name
        df.at[i, "avg_response_sec"] = float(resp)
        df.at[i, "report_rate"] = float(report)
        df.at[i, "training_completed"] = training
        df.at[i, "days_since_training"] = 540 if training == 0 else 60
        for m, r in rates.items():
            sims = 10
            df.at[i, f"{m}_sims"] = sims
            df.at[i, f"{m}_fails"] = int(round(r / 100 * sims))
        avg = np.mean(list(rates.values()))
        df.at[i, "_z"] = (avg - 45) / 20

    # Renumber so the showcase people carry the prototype's IDs EMP-101..107.
    showcase_names = [s[0] for s in SHOWCASE]
    order = [df.index[df.name == n][0] for n in showcase_names]
    rest = [i for i in df.index if i not in order]
    df = df.loc[order + rest].reset_index(drop=True)
    df["id"] = [f"EMP-{101 + i}" for i in range(len(df))]

    # Label: did the person click the NEXT (held-out) simulation?
    impulsive = np.log(df.avg_response_sec)
    worst_rate = np.max([df[f"{m}_fails"] / df[f"{m}_sims"] for m in MODALITIES], axis=0)
    logit = (
        1.05 * df._z
        - 0.55 * (impulsive - 4.0)
        - 0.012 * (df.report_rate - 35)
        - 0.12 * df.training_completed
        + 0.0018 * (df.days_since_training - 150)
        - 0.35 * df.mfa_enabled
        + 0.008 * (df.after_hours_pct - 22)
        + 0.25 * (df.seniority == 2)
        # Non-linear effects: training protection fades sharply after ~6 months,
        # and impulsive clickers with a weak modality are disproportionately exposed.
        + 0.9 * (df.days_since_training > 180) * (df.training_completed > 0)
        + 0.9 * ((df.avg_response_sec < 30) & (worst_rate > 0.6))
        - 0.6 * ((df.report_rate > 60) & (df.mfa_enabled == 1))
        - 0.75
    )
    p = _sigmoid(logit + rng.normal(0, 0.35, len(df)))
    df["clicked_next"] = (rng.random(len(df)) < p).astype(int)
    return df.drop(columns=["_z"])


# --------------------------------------------------------------------------- #
# Content corpora
# --------------------------------------------------------------------------- #
PHISH_TEXT_PARTS = {
    "open": ["Dear user,", "Dear employee,", "Attention:", "Hello,", "Dear valued customer,", "Hi,",
             "Dear account holder,", "URGENT -"],
    "hook": [
        "we detected unusual sign-in activity on your account",
        "your mailbox has exceeded its storage limit",
        "your password expires today",
        "a payment to your account has failed",
        "your payroll direct deposit information must be updated",
        "an invoice is overdue and late fees will apply",
        "your account has been temporarily suspended",
        "a document has been shared with you that requires verification",
        "the CEO needs a quick favour while travelling",
        "your parcel could not be delivered",
        "you have a pending wire transfer awaiting approval",
        "your benefits enrollment will be cancelled",
    ],
    "action": [
        "verify your credentials immediately",
        "click the link below to confirm your identity",
        "log in within 24 hours to avoid permanent suspension",
        "reset your password now using the secure portal",
        "process the wire transfer before end of day and keep this confidential",
        "buy gift cards and send me the codes",
        "scan the QR code to complete payment",
        "confirm your banking details on the attached form",
        "enter your MFA code on the verification page",
        "open the attached invoice and enable macros",
    ],
    "threat": ["or your access will be revoked.", "failure to act will result in account closure.",
               "this is time sensitive.", "do not contact IT about this.", "act now to avoid penalties.",
               "", "", "thank you for your cooperation."],
    "sign": ["IT Security Team", "Account Services", "Payroll Department", "Help Desk", "Sent from my iPhone",
             "Microsoft 365 Team", "Billing Department", "HR Services"],
}
LEGIT_TEXT_PARTS = {
    "open": ["Hi team,", "Hello everyone,", "Hi Sam,", "Good morning,", "Hi all,", "Dear colleagues,", "Hi,"],
    "hook": [
        "the quarterly all-hands is moved to Thursday at 3pm",
        "planned maintenance on the VPN runs Saturday 06:00 to 08:00",
        "the Q3 roadmap draft is ready for comments in the shared drive",
        "lunch and learn on data privacy is next Wednesday",
        "please remember expense reports are due on the 30th",
        "the new coffee machine on floor 3 is installed",
        "your leave request for next Friday was approved",
        "the security team will run a fire drill tomorrow morning",
        "benefits open enrollment starts next month through the usual HR portal",
        "your password will expire in 14 days per our standard policy",
        "the invoice from our regular vendor has been approved by finance",
        "the client meeting notes are attached for reference",
    ],
    "action": [
        "no action is needed from you",
        "you can review it whenever convenient",
        "let me know if you have questions",
        "change it through the self-service portal you already use",
        "feel free to reply with any feedback",
        "please add it to your calendar",
        "contact the service desk on the number in the intranet directory if anything looks odd",
        "we will share the recording afterwards",
    ],
    "threat": ["", "Thanks!", "Cheers,", "Best regards,", "Have a great week.", "Thanks for your patience."],
    "sign": ["Maria from Facilities", "The People Team", "Jonas (IT Service Desk)", "Finance Operations",
             "Priya", "Office Management", "Internal Comms"],
}

VISH_PARTS = {
    "open": ["Hi, this is the IT helpdesk.", "Hello, I am calling from your bank's fraud department.",
             "Hey, it's the CEO, I am at the airport.", "This is an automated security line.",
             "Hi, this is Microsoft support.", "Hello, this is payroll calling about your salary."],
    "hook": ["We detected unusual activity on your workstation.", "My corporate card was declined.",
             "Your account will be locked in ten minutes.", "There is a suspicious transaction on your account.",
             "We need to verify your identity for the salary update.", "Your computer is sending virus alerts."],
    "action": ["Please read me the six digit code we just texted you.",
               "Enter your MFA pin after the tone.", "I need you to buy gift cards and send me the codes.",
               "Approve the authentication request on your phone right now.",
               "Install the remote support tool so I can fix it.",
               "Confirm your full card number and security code.",
               "Transfer the funds to the safe account I will give you."],
    "close": ["Quickly, my flight is boarding.", "Do not hang up or the case will escalate.",
              "Keep this between us.", "This must happen in the next five minutes.", ""],
}
LEGIT_CALL_PARTS = {
    "open": ["Hi, it's Jonas from the service desk returning your ticket.", "Hello, this is reception.",
             "Hi, this is Maria from facilities.", "Hey, it's your manager.", "Hello, this is the dentist's office."],
    "hook": ["Your laptop replacement has arrived.", "Your visitor is waiting in the lobby.",
             "The meeting room booking for tomorrow is confirmed.", "I wanted to check on the project timeline.",
             "We are confirming your appointment on Tuesday."],
    "action": ["You can pick it up at the desk any time today.", "No need to share any details, just come down.",
               "Call me back on my extension when you are free.", "Reply to the ticket if you have questions.",
               "If you need to reschedule, call the number on our website."],
    "close": ["Thanks, bye.", "Have a good day.", "Talk soon.", ""],
}


def _compose(parts, rng, keys=("open", "hook", "action", "threat", "sign")):
    out = []
    for k in keys:
        if k in parts:
            out.append(rng.choice(parts[k]))
    return " ".join(s for s in out if s)


def generate_text_corpus(n: int = 3200, seed: int = SEED):
    rng = random.Random(seed)
    texts, labels = [], []
    for i in range(n):
        phish = i % 2 == 0
        parts = PHISH_TEXT_PARTS if phish else LEGIT_TEXT_PARTS
        t = _compose(parts, rng)
        # Label noise and cross-over so the problem is not trivially separable.
        if rng.random() < 0.12:
            other = LEGIT_TEXT_PARTS if phish else PHISH_TEXT_PARTS
            t += " " + rng.choice(other["hook"])
        if rng.random() < 0.08:
            t = t.replace("immediately", "").replace("URGENT -", "")
        texts.append(t)
        # ~4% label noise: mis-reported or ambiguous messages in a real inbox.
        labels.append(int(phish) if rng.random() > 0.04 else int(not phish))
    return texts, labels


def generate_vishing_corpus(n: int = 1600, seed: int = SEED + 1):
    rng = random.Random(seed)
    texts, labels = [], []
    for i in range(n):
        phish = i % 2 == 0
        parts = VISH_PARTS if phish else LEGIT_CALL_PARTS
        t = _compose(parts, rng, keys=("open", "hook", "action", "close"))
        if rng.random() < 0.1:
            other = LEGIT_CALL_PARTS if phish else VISH_PARTS
            t += " " + rng.choice(other["hook"])
        texts.append(t)
        # ~4% label noise: mis-reported or ambiguous messages in a real inbox.
        labels.append(int(phish) if rng.random() > 0.04 else int(not phish))
    return texts, labels
