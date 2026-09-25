"""Runtime engine: loads trained models, holds organisation state, and runs
prediction, SHAP explanation, campaign simulation and training assignment."""
from __future__ import annotations

import json
import math
import re
import threading
import time
import uuid
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from ml.features import EMP_COLS, EMP_LABELS, EMP_UNITS, MODALITIES, MODULE_FOR_FEATURE, MODULE_MODALITY, employee_matrix
from .content import MODULES, QUIZ, TEMPLATES

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
DATA = ROOT / "data"
STATE = DATA / "state"

HIGH, MEDIUM = 60.0, 30.0
MOD_LABEL = {"text": "Text", "image": "Image", "url": "URL", "audio": "Audio"}
DIFFICULTY_SHIFT = {"Easy": -0.5, "Medium": 0.0, "Hard": 0.45}


def level(score: float) -> str:
    return "High" if score >= HIGH else "Medium" if score >= MEDIUM else "Low"


def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        bundle = joblib.load(MODELS / "risk_model.joblib")
        self.model = bundle["model"]
        self.background = bundle["background"]
        # Probability-space SHAP: every attribution reads as percentage points of click probability.
        self.explainer = shap.TreeExplainer(self.model, data=self.background, model_output="probability",
                                            feature_perturbation="interventional")
        self.text_model = joblib.load(MODELS / "text_model.joblib")
        self.voice_model = joblib.load(MODELS / "voice_model.joblib")
        self.report = json.loads((MODELS / "model_report.json").read_text())
        self.base_value = float(np.ravel(self.explainer.expected_value)[-1])
        self.load_state()

    # ------------------------------------------------------------------ state
    def load_state(self):
        with self.lock:
            if (STATE / "employees.csv").exists():
                self.df = pd.read_csv(STATE / "employees.csv", keep_default_na=False)
                meta = json.loads((STATE / "meta.json").read_text())
                self.events, self.campaigns, self.trend = meta["events"], meta["campaigns"], meta["trend"]
                if "flagged" not in self.df.columns:
                    self.df["flagged"] = 0
                self._rescore()
            else:
                self.reset()

    def reset(self):
        with self.lock:
            self.df = pd.read_csv(DATA / "employees_seed.csv")
            self.df["assigned_module"] = ""
            self.df["assigned_reason"] = ""
            self.df["assigned_at"] = 0.0
            self.df["completed"] = 0
            self.df["quiz_score"] = -1
            self.df["flagged"] = 0  # fell for a phish in the training quiz -> needs attention
            self.events, self.campaigns = [], []
            self._rescore()
            self.auto_assign(record=False)
            # Seed realistic history: people with prior training finished some of their modules.
            rng = np.random.default_rng(11)
            for i in self.df.index[self.df.assigned_module != ""]:
                if self.df.at[i, "training_completed"] >= 2 and rng.random() < 0.7:
                    self.df.at[i, "completed"] = 1
                    self.df.at[i, "quiz_score"] = int(rng.choice([4, 5]))
            self._seed_events(rng)
            self._seed_trend()
            self.save()

    def save(self):
        STATE.mkdir(parents=True, exist_ok=True)
        self.df.drop(columns=["risk"], errors="ignore").to_csv(STATE / "employees.csv", index=False)
        (STATE / "meta.json").write_text(json.dumps(
            {"events": self.events[:400], "campaigns": self.campaigns, "trend": self.trend}))

    def _rescore(self, idx=None):
        X = employee_matrix(self.df if idx is None else self.df.loc[idx])
        p = self.model.predict_proba(X)[:, 1] * 100
        if idx is None:
            self.df["risk"] = np.round(p, 1)
        else:
            self.df.loc[idx, "risk"] = np.round(p, 1)

    def _seed_events(self, rng):
        now = time.time()
        templates = [(m, t) for m in MODALITIES for t in TEMPLATES[m]]
        sample = self.df.sample(14, random_state=3)
        for k, (_, e) in enumerate(sample.iterrows()):
            m, t = templates[k % len(templates)]
            clicked = rng.random() < e.risk / 100
            outcome = "Clicked" if clicked else ("Reported" if rng.random() < e.report_rate / 100 else "Ignored")
            self.events.append({"id": uuid.uuid4().hex[:8], "emp_id": e.id, "emp": e["name"], "dept": e.dept,
                                "modality": m, "template": t["title"], "status": outcome,
                                "at": now - (k + 1) * 60 * (7 + 11 * k), "delta": round(float(rng.normal(6 if clicked else -3, 2)), 1),
                                "campaign": "Q3 baseline programme"})

    def _seed_trend(self):
        cur = self.summary_numbers()
        offsets = [11.2, 10.6, 10.9, 9.4, 8.1, 7.7, 6.0, 4.9, 4.2, 2.6, 1.3]
        click_off = [7.9, 7.4, 7.6, 6.6, 5.8, 5.1, 4.2, 3.3, 2.9, 1.8, 0.8]
        week = int(time.strftime("%V"))
        self.trend = [{"label": f"W{week - 11 + i}", "avg_risk": round(cur["avg_risk"] + o, 1),
                       "click_rate": round(cur["click_rate"] + c, 1)} for i, (o, c) in enumerate(zip(offsets, click_off))]
        self._update_trend()

    def _update_trend(self):
        cur = self.summary_numbers()
        label = f"W{int(time.strftime('%V'))}"
        point = {"label": label, "avg_risk": cur["avg_risk"], "click_rate": cur["click_rate"]}
        if self.trend and self.trend[-1]["label"] == label:
            self.trend[-1] = point
        else:
            self.trend.append(point)
        self.trend = self.trend[-12:]

    # --------------------------------------------------------------- summaries
    def summary_numbers(self):
        df = self.df
        sims = sum(df[f"{m}_sims"].sum() for m in MODALITIES)
        fails = sum(df[f"{m}_fails"].sum() for m in MODALITIES)
        assigned = (df.assigned_module != "").sum()
        return {
            "staff": int(len(df)),
            "avg_risk": round(float(df.risk.mean()), 1),
            "high_risk": int((df.risk >= HIGH).sum()),
            "medium_risk": int(((df.risk >= MEDIUM) & (df.risk < HIGH)).sum()),
            "low_risk": int((df.risk < MEDIUM).sum()),
            "click_rate": round(float(fails / sims * 100), 1),
            "simulations": int(sims),
            "report_rate": round(float(df.report_rate.mean()), 1),
            "training_assigned": int(assigned),
            "training_completed": int(((df.assigned_module != "") & (df.completed == 1)).sum()),
            "training_completion": round(float(((df.assigned_module != "") & (df.completed == 1)).sum() / max(assigned, 1) * 100), 1),
        }

    def weakness(self, row) -> str:
        rates = {m: row[f"{m}_fails"] / max(row[f"{m}_sims"], 1) for m in MODALITIES}
        return max(rates, key=rates.get)

    def employee_row(self, row) -> dict:
        return {
            "id": row["id"], "name": row["name"], "dept": row["dept"], "risk": float(row["risk"]),
            "level": level(row["risk"]), "weakness": self.weakness(row),
            "rates": {m: round(row[f"{m}_fails"] / max(row[f"{m}_sims"], 1) * 100, 1) for m in MODALITIES},
            "avg_response_sec": float(row["avg_response_sec"]), "report_rate": float(row["report_rate"]),
            "training_completed": int(row["training_completed"]), "days_since_training": int(row["days_since_training"]),
            "mfa_enabled": int(row["mfa_enabled"]), "seniority": int(row["seniority"]),
            "assigned_module": row["assigned_module"], "assigned_reason": row["assigned_reason"],
            "completed": bool(row["completed"]), "quiz_score": int(row["quiz_score"]),
            "flagged": bool(row["flagged"]),
        }

    def dashboard(self):
        with self.lock:
            df = self.df
            modality = []
            for m in MODALITIES:
                s, f = int(df[f"{m}_sims"].sum()), int(df[f"{m}_fails"].sum())
                modality.append({"modality": m, "label": MOD_LABEL[m], "sims": s, "fails": f,
                                 "fail_rate": round(f / s * 100, 1)})
            depts = []
            for d, g in df.groupby("dept"):
                rates = {m: round(g[f"{m}_fails"].sum() / g[f"{m}_sims"].sum() * 100, 1) for m in MODALITIES}
                depts.append({"dept": d, "headcount": int(len(g)), "avg_risk": round(float(g.risk.mean()), 1),
                              "high_risk": int((g.risk >= HIGH).sum()), "rates": rates,
                              "primary": max(rates, key=rates.get)})
            depts.sort(key=lambda d: -d["avg_risk"])
            hist, edges = np.histogram(df.risk, bins=10, range=(0, 100))
            return {
                "kpis": self.summary_numbers(),
                "baseline": self.trend[0] if self.trend else None,
                "modality": modality,
                "departments": depts,
                "trend": self.trend,
                "distribution": [{"bin": f"{int(edges[i])}-{int(edges[i + 1])}", "from": int(edges[i]),
                                  "count": int(hist[i])} for i in range(10)],
                "activity": sorted(self.events, key=lambda e: -e["at"])[:12],
                "top_risk": [self.employee_row(r) for _, r in df.nlargest(6, "risk").iterrows()],
                "attention": self.attention(8),
                "flagged": int(df.flagged.sum()),
            }

    def employees(self, search="", dept="All", lvl="All", weak="All", sort="risk", order="desc", page=1, size=25):
        with self.lock:
            rows = [self.employee_row(r) for _, r in self.df.iterrows()]
        q = search.strip().lower()
        if q:
            rows = [r for r in rows if q in r["name"].lower() or q in r["id"].lower()]
        if dept != "All":
            rows = [r for r in rows if r["dept"] == dept]
        if lvl == "Attention":
            rows = [r for r in rows if r["flagged"] or r["level"] == "High"]
        elif lvl != "All":
            rows = [r for r in rows if r["level"] == lvl]
        if weak != "All":
            rows = [r for r in rows if r["weakness"] == weak]
        keyf = {"risk": lambda r: r["risk"], "name": lambda r: r["name"], "dept": lambda r: r["dept"],
                "id": lambda r: int(r["id"].split("-")[1])}.get(sort, lambda r: r["risk"])
        rows.sort(key=keyf, reverse=(order == "desc"))
        if lvl == "Attention":
            rows.sort(key=lambda r: not r["flagged"])  # stable: quiz failures first, then by risk
        total = len(rows)
        start = (max(page, 1) - 1) * size
        return {"total": total, "page": page, "size": size, "rows": rows[start:start + size],
                "departments": sorted(self.df.dept.unique().tolist())}

    def attention(self, n=8):
        """People who need help: anyone who fell for a quiz phish first, then the highest risk."""
        df = self.df.assign(_f=self.df.flagged.astype(int))
        top = df[(df._f == 1) | (df.risk >= HIGH)].sort_values(["_f", "risk"], ascending=False).head(n)
        return [self.employee_row(r) for _, r in top.iterrows()]

    def get_index(self, emp_id):
        emp_id = str(emp_id).strip().upper()
        if emp_id.isdigit():
            emp_id = f"EMP-{emp_id}"
        elif emp_id.startswith("EMP") and not emp_id.startswith("EMP-"):
            emp_id = "EMP-" + emp_id[3:]
        idx = self.df.index[self.df.id == emp_id]
        if len(idx) == 0:
            raise KeyError(emp_id)
        return idx[0]

    # --------------------------------------------------------------------- XAI
    def _shap_row(self, X: pd.DataFrame):
        sv = np.asarray(self.explainer.shap_values(X))
        if sv.ndim == 3:
            sv = sv[..., 1]
        return sv[0]

    def explain_vector(self, features: dict):
        X = pd.DataFrame([[float(features[c]) for c in EMP_COLS]], columns=EMP_COLS)
        prob = float(self.model.predict_proba(X)[0, 1])
        sv = self._shap_row(X)
        contribs = [{"feature": c, "label": EMP_LABELS[c], "unit": EMP_UNITS[c], "value": float(X.iloc[0][c]),
                     "shap": round(float(sv[j]) * 100, 2)} for j, c in enumerate(EMP_COLS)]
        contribs.sort(key=lambda d: -abs(d["shap"]))
        return {"risk": round(prob * 100, 1), "level": level(prob * 100), "base": round(self.base_value * 100, 1),
                "contributions": contribs}

    def explain_employee(self, emp_id):
        with self.lock:
            i = self.get_index(emp_id)
            row = self.df.loc[i]
            X = employee_matrix(self.df.loc[[i]])
        feats = X.iloc[0].to_dict()
        exp = self.explain_vector(feats)
        exp["employee"] = self.employee_row(row)
        exp["narrative"] = self._narrative(row, exp)
        exp["recommendation"] = self._recommend(exp["contributions"])
        exp["counterfactuals"] = self._counterfactuals(feats, exp["risk"])
        return exp

    def _fmt(self, c):
        v, u = c["value"], c["unit"]
        if u == "bool":
            return "yes" if v >= 0.5 else "no"
        if u == "%":
            return f"{v:.0f}%"
        if u == "s":
            return f"{v:.0f} s"
        if u:
            return f"{v:.0f} {u}"
        return f"{v:.0f}"

    def _narrative(self, row, exp):
        first = row["name"].split()[0]
        ups = [c for c in exp["contributions"] if c["shap"] > 0.5]
        downs = [c for c in exp["contributions"] if c["shap"] < -0.5]
        parts = [f"The model puts {first}'s probability of clicking the next simulation at {exp['risk']:.0f}%, "
                 f"against a population baseline of {exp['base']:.0f}%."]
        if ups:
            u = ups[0]
            parts.append(f"The biggest driver is {u['label'].lower()} ({self._fmt(u)}), adding {u['shap']:.1f} points.")
            if len(ups) > 1:
                parts.append(f"{ups[1]['label']} ({self._fmt(ups[1])}) adds another {ups[1]['shap']:.1f}.")
        if downs:
            d = downs[0]
            parts.append(f"Working in their favour: {d['label'].lower()} ({self._fmt(d)}) removes {abs(d['shap']):.1f} points.")
        return " ".join(parts)

    def _recommend(self, contribs):
        for c in contribs:
            if c["shap"] > 0 and c["feature"] in MODULE_FOR_FEATURE:
                return {"module": MODULE_FOR_FEATURE[c["feature"]], "driver": c["feature"],
                        "driver_label": c["label"], "shap": c["shap"]}
        return {"module": "Security Awareness Refresher", "driver": None, "driver_label": None, "shap": 0}

    def _counterfactuals(self, feats, current):
        """What single realistic change would lower this person's risk the most?"""
        changes = [
            ("Complete one adaptive module now", {"training_completed": feats["training_completed"] + 1, "days_since_training": 0}),
            ("Report 30 points more of suspicious mail", {"report_rate": min(100, feats["report_rate"] + 30)}),
            ("Take 3x longer before clicking", {"avg_response_sec": feats["avg_response_sec"] * 3}),
            ("Enable MFA", {"mfa_enabled": 1}),
        ]
        rates = {m: feats[f"{m}_fail_rate"] for m in MODALITIES}
        worst = max(rates, key=rates.get)
        changes.append((f"Halve the {MOD_LABEL[worst]} failure rate", {f"{worst}_fail_rate": rates[worst] / 2}))
        out = []
        for label, delta in changes:
            if all(feats.get(k) == v for k, v in delta.items()):
                continue
            f2 = {**feats, **delta}
            X = pd.DataFrame([[float(f2[c]) for c in EMP_COLS]], columns=EMP_COLS)
            p = float(self.model.predict_proba(X)[0, 1]) * 100
            out.append({"change": label, "risk": round(p, 1), "delta": round(p - current, 1)})
        out.sort(key=lambda d: d["delta"])
        return out

    def global_explanations(self):
        r = self.report["risk"]
        return {"importance": r["global_importance"], "beeswarm": r["beeswarm"], "base": r["shap_expected_value"]}

    def high_risk(self, n=12):
        with self.lock:
            return [self.employee_row(r) for _, r in self.df.nlargest(n, "risk").iterrows()]

    # -------------------------------------------------------- content models
    def analyze_text(self, text: str, kind: str = "email"):
        art = self.voice_model if kind == "voice" else self.text_model
        vec, clf = art["vectorizer"], art["model"]
        x = vec.transform([text])
        prob = float(clf.predict_proba(x)[0, 1])
        names = vec.get_feature_names_out()
        coef = clf.coef_[0]
        terms = []
        for j, v in zip(x.indices, x.data):
            terms.append({"term": names[j], "weight": round(float(v * coef[j]), 4)})
        terms.sort(key=lambda t: -abs(t["weight"]))
        # Token-level attribution: each word gets its unigram weight plus half of every bigram it belongs to.
        tw = {t["term"]: t["weight"] for t in terms}
        tokens = []
        pattern = re.compile(r"[\w$']+|[^\w$']+", re.UNICODE)
        words = [m.group(0) for m in pattern.finditer(text)]
        lower = [w.lower() for w in words]
        word_idx = [k for k, w in enumerate(words) if re.match(r"[\w$']", w)]
        weights = {k: tw.get(lower[k], 0.0) for k in word_idx}
        for a, b in zip(word_idx, word_idx[1:]):
            bg = f"{lower[a]} {lower[b]}"
            if bg in tw:
                weights[a] += tw[bg] / 2
                weights[b] += tw[bg] / 2
        for k, w in enumerate(words):
            tokens.append({"text": w, "weight": round(weights.get(k, 0.0), 4)})
        return {"probability": round(prob * 100, 1), "verdict": "Phishing" if prob >= 0.5 else "Looks legitimate",
                "intercept": round(float(clf.intercept_[0]), 3), "terms": terms[:12], "tokens": tokens,
                "model": self.report["voice" if kind == "voice" else "text"]["name"]}

    # -------------------------------------------------------------- campaigns
    def campaign_forecast(self, modality, dept, difficulty):
        with self.lock:
            g = self.df if dept == "All" else self.df[self.df.dept == dept]
            probs = self._click_probs(g, modality, difficulty)
            top = g.assign(p=probs).nlargest(5, "p")
            return {"targets": int(len(g)), "expected_click_rate": round(float(np.mean(probs) * 100), 1),
                    "expected_clicks": int(round(float(np.sum(probs)))),
                    "most_likely": [{"id": r.id, "name": r["name"], "dept": r.dept, "p": round(float(r.p) * 100, 1)}
                                    for _, r in top.iterrows()]}

    def _click_probs(self, g, modality, difficulty):
        # Blend the person's overall model risk with their record on this modality (Laplace-smoothed).
        mod_rate = (g[f"{modality}_fails"] + 1) / (g[f"{modality}_sims"] + 2)
        risk = (g.risk / 100).clip(0.01, 0.99)
        z = 0.5 * np.log(risk / (1 - risk)) + 0.7 * np.log(mod_rate / (1 - mod_rate)) + DIFFICULTY_SHIFT.get(difficulty, 0) - 0.3
        return (1 / (1 + np.exp(-z))).values

    def launch_campaign(self, name, modality, template_id, dept, difficulty):
        tmpl = next((t for t in TEMPLATES[modality] if t["id"] == template_id), TEMPLATES[modality][0])
        rng = np.random.default_rng()
        with self.lock:
            idx = self.df.index if dept == "All" else self.df.index[self.df.dept == dept]
            g = self.df.loc[idx]
            before = g.risk.copy()
            probs = self._click_probs(g, modality, difficulty)
            now = time.time()
            clicked = reported = ignored = 0
            outcomes = {}
            for (i, row), p in zip(g.iterrows(), probs):
                r = rng.random()
                if r < p:
                    out = "Clicked"; clicked += 1
                    self.df.at[i, f"{modality}_fails"] += 1
                    t = float(np.clip(rng.lognormal(math.log(max(row.avg_response_sec, 5)), 0.4), 3, 900))
                    self.df.at[i, "avg_response_sec"] = round(0.8 * row.avg_response_sec + 0.2 * t, 1)
                    self.df.at[i, "report_rate"] = round(0.9 * row.report_rate, 1)
                elif rng.random() < row.report_rate / 100:
                    out = "Reported"; reported += 1
                    self.df.at[i, "report_rate"] = round(min(100, 0.9 * row.report_rate + 10), 1)
                else:
                    out = "Ignored"; ignored += 1
                self.df.at[i, f"{modality}_sims"] += 1
                outcomes[i] = out
            self._rescore(idx)
            after = self.df.loc[idx, "risk"]
            cid = uuid.uuid4().hex[:8]
            cname = name or f"{tmpl['title']} ({dept})"
            # Log every clicker/reporter, plus a sample of the rest.
            logged = 0
            for i, out in outcomes.items():
                if out == "Ignored" and logged > 40:
                    continue
                row = self.df.loc[i]
                self.events.append({"id": uuid.uuid4().hex[:8], "emp_id": row.id, "emp": row["name"], "dept": row.dept,
                                    "modality": modality, "template": tmpl["title"], "status": out,
                                    "at": now + rng.random() * 5, "delta": round(float(after[i] - before[i]), 1),
                                    "campaign": cname})
                logged += 1
            self.events = sorted(self.events, key=lambda e: -e["at"])[:400]
            assigned = self.auto_assign(subset=idx)
            camp = {"id": cid, "name": cname, "modality": modality, "template": tmpl["title"], "dept": dept,
                    "difficulty": difficulty, "at": now, "targets": int(len(idx)), "clicked": clicked,
                    "reported": reported, "ignored": ignored,
                    "click_rate": round(clicked / max(len(idx), 1) * 100, 1),
                    "expected_click_rate": round(float(np.mean(probs) * 100), 1),
                    "avg_risk_before": round(float(before.mean()), 1), "avg_risk_after": round(float(after.mean()), 1),
                    "auto_assigned": len(assigned)}
            self.campaigns.insert(0, camp)
            self._update_trend()
            self.save()
            return {**camp, "assignments": assigned[:10]}

    # --------------------------------------------------------------- training
    def auto_assign(self, subset=None, record=True):
        """XAI-driven assignment: each at-risk person gets the module that targets
        their single largest positive SHAP driver - the same attribution the XAI page shows."""
        with self.lock:
            idx = self.df.index if subset is None else subset
            cand = [i for i in idx if self.df.at[i, "risk"] >= MEDIUM and
                    (self.df.at[i, "assigned_module"] == "" or self.df.at[i, "completed"] == 1)]
            if not cand:
                return []
            X = employee_matrix(self.df.loc[cand])
            sv = np.asarray(self.explainer.shap_values(X))
            if sv.ndim == 3:
                sv = sv[..., 1]
            out = []
            for k, i in enumerate(cand):
                order = np.argsort(-sv[k])
                module, driver = "Security Awareness Refresher", None
                for j in order:
                    col = EMP_COLS[j]
                    if sv[k, j] > 0 and col in MODULE_FOR_FEATURE:
                        module, driver = MODULE_FOR_FEATURE[col], col
                        break
                if self.df.at[i, "completed"] == 1 and self.df.at[i, "assigned_module"] == module and self.df.at[i, "risk"] < HIGH:
                    continue  # already completed the right module and not high risk
                self.df.at[i, "assigned_module"] = module
                self.df.at[i, "assigned_reason"] = (f"Top SHAP driver: {EMP_LABELS[driver]}" if driver else "General refresher")
                self.df.at[i, "assigned_at"] = time.time()
                self.df.at[i, "completed"] = 0
                self.df.at[i, "quiz_score"] = -1
                out.append({"id": self.df.at[i, "id"], "name": self.df.at[i, "name"], "module": module,
                            "reason": self.df.at[i, "assigned_reason"], "risk": float(self.df.at[i, "risk"])})
            if record:
                self._update_trend()
                self.save()
            return out

    def training(self, emp_id):
        with self.lock:
            i = self.get_index(emp_id)
            row = self.df.loc[i]
            emp = self.employee_row(row)
        module_name = emp["assigned_module"] or MODULE_FOR_FEATURE.get(f"{emp['weakness']}_fail_rate")
        module = MODULES[module_name]
        focus = MODULE_MODALITY.get(module_name) or emp["weakness"]
        questions = [q for q in QUIZ if q["modality"] == focus]
        others = [q for q in QUIZ if q["modality"] != focus]
        # Interleave the other modalities so every quiz is multimodal.
        by_mod = {m: [q for q in others if q["modality"] == m] for m in MODALITIES}
        k = 0
        while len(questions) < 5:
            for m in MODALITIES:
                if k < len(by_mod[m]) and len(questions) < 5:
                    questions.append(by_mod[m][k])
            k += 1
        public = [{key: v for key, v in q.items() if key not in ("answer", "explain")} for q in questions[:5]]
        return {"employee": emp, "module": {"name": module_name, **module}, "questions": public,
                "assigned": bool(emp["assigned_module"])}

    def check_answer(self, qid, answer, emp_id=None):
        """Instant feedback for one quiz question. With an employee, the answer counts as a
        simulation on their record: a wrong answer is a click and puts them on the attention list."""
        q = next((q for q in QUIZ if q["id"] == qid), None)
        if q is None:
            raise KeyError(qid)
        correct = answer == q["answer"]
        out = {"id": qid, "correct": correct, "answer": q["answer"], "explain": q["explain"]}
        if not emp_id:
            return out
        with self.lock:
            i = self.get_index(emp_id)
            m = q["modality"]
            before = float(self.df.at[i, "risk"])
            self.df.at[i, f"{m}_sims"] += 1
            if not correct:
                self.df.at[i, f"{m}_fails"] += 1
                self.df.at[i, "flagged"] = 1
            self._rescore([i])
            after = float(self.df.at[i, "risk"])
            if not correct:
                self.events.insert(0, {"id": uuid.uuid4().hex[:8], "emp_id": self.df.at[i, "id"], "emp": self.df.at[i, "name"],
                                       "dept": self.df.at[i, "dept"], "modality": m, "template": "Spot the phish quiz",
                                       "status": "Clicked", "at": time.time(), "delta": round(after - before, 1),
                                       "campaign": "Training quiz"})
            self._update_trend()
            self.save()
        return {**out, "risk_before": before, "risk": after, "level": level(after), "flagged": bool(self.df.at[i, "flagged"])}

    def submit_quiz(self, emp_id, answers: dict):
        bank = {q["id"]: q for q in QUIZ}
        results = []
        for qid, ans in answers.items():
            q = bank.get(qid)
            if q:
                results.append({"id": qid, "correct": ans == q["answer"], "answer": q["answer"], "given": ans,
                                "explain": q["explain"], "modality": q["modality"]})
        score = sum(r["correct"] for r in results)
        need = max(1, math.ceil(len(results) * 0.8))
        passed = score >= need
        with self.lock:
            i = self.get_index(emp_id)
            before_exp = self.explain_employee(emp_id)
            before = before_exp["risk"]
            self.df.at[i, "quiz_score"] = score
            if passed:
                self.df.at[i, "flagged"] = 0
                if not self.df.at[i, "assigned_module"]:
                    self.df.at[i, "assigned_module"] = self.training(emp_id)["module"]["name"]
                    self.df.at[i, "assigned_reason"] = "Self-enrolled"
                self.df.at[i, "completed"] = 1
                self.df.at[i, "training_completed"] += 1
                self.df.at[i, "days_since_training"] = 0
                self.df.at[i, "report_rate"] = round(min(100, float(self.df.at[i, "report_rate"]) + 8), 1)
            self._rescore([i])
            after_exp = self.explain_employee(emp_id)
            after = after_exp["risk"]
            now = time.time()
            self.events.insert(0, {"id": uuid.uuid4().hex[:8], "emp_id": emp_id, "emp": self.df.at[i, "name"],
                                   "dept": self.df.at[i, "dept"], "modality": "training",
                                   "template": self.df.at[i, "assigned_module"] or "Training quiz",
                                   "status": "Passed training" if passed else "Failed quiz", "at": now,
                                   "delta": round(after - before, 1), "campaign": "Adaptive training"})
            self._update_trend()
            self.save()

        # What changed, feature by feature, and how much each change moved the risk (SHAP before vs after).
        b = {c["feature"]: c for c in before_exp["contributions"]}
        changes = []
        for c in after_exp["contributions"]:
            old = b[c["feature"]]
            if abs(c["value"] - old["value"]) > 1e-9:
                changes.append({"feature": c["feature"], "label": c["label"], "unit": c["unit"],
                                "before": old["value"], "after": c["value"],
                                "shap_before": old["shap"], "shap_after": c["shap"],
                                "effect": round(c["shap"] - old["shap"], 2)})
        changes.sort(key=lambda d: d["effect"])
        still = [c for c in after_exp["contributions"] if c["shap"] > 0.5][:3]
        return {"score": score, "total": len(results), "needed": need, "passed": passed, "results": results,
                "risk_before": before, "risk_after": after, "level_before": level(before), "level_after": level(after),
                "base": after_exp["base"], "changes": changes, "remaining_drivers": still,
                "next_steps": [c for c in after_exp["counterfactuals"] if c["delta"] < 0][:3]}


engine: Engine | None = None


def get_engine() -> Engine:
    global engine
    if engine is None:
        engine = Engine()
    return engine
