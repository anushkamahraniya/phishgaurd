"""Train every PhishGuard model and write artefacts to backend/models/.

Run from the backend folder:  .venv\\Scripts\\python -m ml.train
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import shap
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data_gen import generate_employees, generate_text_corpus, generate_vishing_corpus
from .features import EMP_COLS, EMP_LABELS, employee_matrix

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
DATA = ROOT / "data"
SEED = 7


def _metrics(y_true, prob, threshold=0.5):
    pred = (prob >= threshold).astype(int)
    fpr, tpr, _ = roc_curve(y_true, prob)
    # Down-sample the ROC curve for the UI.
    idx = np.unique(np.linspace(0, len(fpr) - 1, min(60, len(fpr))).astype(int))
    return {
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, pred)), 4),
        "f1": round(float(f1_score(y_true, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, prob)), 4),
        "brier": round(float(brier_score_loss(y_true, prob)), 4),
        "confusion": confusion_matrix(y_true, pred).tolist(),  # [[TN, FP], [FN, TP]]
        "roc": [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in idx],
        "n_test": int(len(y_true)),
        "positive_rate": round(float(np.mean(y_true)), 4),
    }


# Domain knowledge as monotonic constraints: +1 = can only raise risk, -1 = can only lower it, 0 = free.
# Without these, trees fit noise (e.g. "reporting more phish raises risk"), which makes explanations nonsensical.
MONOTONIC = {
    "url_fail_rate": 1, "text_fail_rate": 1, "image_fail_rate": 1, "audio_fail_rate": 1,
    "avg_response_sec": -1, "report_rate": -1, "training_completed": -1, "days_since_training": 1,
    "mfa_enabled": -1, "after_hours_pct": 1, "seniority": 0, "tenure_years": 0,
}


def make_risk_model():
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_depth=3, min_samples_leaf=15, l2_regularization=1.0,
        monotonic_cst=[MONOTONIC[c] for c in EMP_COLS], random_state=SEED)


def train_risk_model():
    df = generate_employees(SEED)
    X = employee_matrix(df)
    y = df["clicked_next"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)

    gbm = make_risk_model()
    gbm.fit(X_tr, y_tr)
    prob = gbm.predict_proba(X_te)[:, 1]

    baseline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    baseline.fit(X_tr, y_tr)
    base_prob = baseline.predict_proba(X_te)[:, 1]

    cv = cross_val_score(
        make_risk_model(),
        X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED), scoring="roc_auc")

    # SHAP in probability space (interventional, against a background sample),
    # so every attribution reads as "percentage points of click probability".
    background = X_tr.sample(150, random_state=SEED)
    explainer = shap.TreeExplainer(gbm, data=background, model_output="probability",
                                   feature_perturbation="interventional")
    sample = X_te.sample(min(400, len(X_te)), random_state=SEED)
    sv = np.asarray(explainer.shap_values(sample))
    if sv.ndim == 3:  # some shap versions return one array per class
        sv = sv[..., 1]

    rng = np.random.default_rng(SEED)
    importance, beeswarm = [], []
    for j, col in enumerate(EMP_COLS):
        importance.append({"feature": col, "label": EMP_LABELS[col],
                           "mean_abs_shap": round(float(np.mean(np.abs(sv[:, j]))) * 100, 3)})
        vals = sample[col].values
        lo, hi = float(np.min(vals)), float(np.max(vals))
        pick = rng.choice(len(vals), size=min(120, len(vals)), replace=False)
        beeswarm.append({"feature": col, "label": EMP_LABELS[col], "points": [
            {"shap": round(float(sv[i, j]) * 100, 3), "value": float(vals[i]),
             "norm": round((float(vals[i]) - lo) / (hi - lo), 3) if hi > lo else 0.5}
            for i in pick]})
    importance.sort(key=lambda d: -d["mean_abs_shap"])
    order = [d["feature"] for d in importance]
    beeswarm.sort(key=lambda d: order.index(d["feature"]))

    joblib.dump({"model": gbm, "background": background, "columns": EMP_COLS}, MODELS / "risk_model.joblib")
    DATA.mkdir(exist_ok=True)
    df.drop(columns=["clicked_next"]).to_csv(DATA / "employees_seed.csv", index=False)

    return {
        "name": "Employee click-risk model",
        "algorithm": "Gradient-boosted decision trees with monotonic constraints (scikit-learn HistGradientBoosting, 300 trees, depth 3)",
        "monotonic_constraints": MONOTONIC,
        "target": "Clicks the next phishing simulation",
        "features": [{"feature": c, "label": EMP_LABELS[c]} for c in EMP_COLS],
        "n_train": int(len(X_tr)),
        "test": _metrics(y_te, prob),
        "baseline_logreg": _metrics(y_te, base_prob),
        "cv_auc_mean": round(float(cv.mean()), 4),
        "cv_auc_std": round(float(cv.std()), 4),
        "explainer": "SHAP TreeExplainer (interventional, probability output, 150-row background)",
        "shap_expected_value": round(float(np.ravel(explainer.expected_value)[-1]) * 100, 2),
        "global_importance": importance,
        "beeswarm": beeswarm,
    }


def train_text_model(texts, labels, name, target):
    X_tr, X_te, y_tr, y_te = train_test_split(texts, labels, test_size=0.25, stratify=labels, random_state=SEED)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True,
                          token_pattern=r"(?u)\b[\w$']+\b")
    clf = LogisticRegression(C=2.0, max_iter=3000)
    clf.fit(vec.fit_transform(X_tr), y_tr)
    prob = clf.predict_proba(vec.transform(X_te))[:, 1]
    terms = np.array(vec.get_feature_names_out())
    coef = clf.coef_[0]
    top = np.argsort(coef)
    return {"vectorizer": vec, "model": clf}, {
        "name": name,
        "algorithm": "TF-IDF (1-2 grams) + logistic regression",
        "target": target,
        "n_train": len(X_tr),
        "vocabulary": int(len(terms)),
        "test": _metrics(np.array(y_te), prob),
        "explainer": "Linear attribution: coefficient x TF-IDF weight per term (exact SHAP for a linear model vs. an empty document)",
        "top_phish_terms": [{"term": terms[i], "weight": round(float(coef[i]), 3)} for i in top[::-1][:15]],
        "top_legit_terms": [{"term": terms[i], "weight": round(float(coef[i]), 3)} for i in top[:15]],
    }


def main():
    MODELS.mkdir(exist_ok=True)
    report = {}
    print("Training employee risk model ...")
    report["risk"] = train_risk_model()
    print(f"  test AUC {report['risk']['test']['roc_auc']}  (baseline {report['risk']['baseline_logreg']['roc_auc']})")

    print("Training email-text phishing classifier ...")
    art, meta = train_text_model(*generate_text_corpus(), "Email text classifier", "Message is phishing")
    joblib.dump(art, MODELS / "text_model.joblib")
    report["text"] = meta
    print(f"  test AUC {meta['test']['roc_auc']}")

    print("Training call-transcript (vishing) classifier ...")
    art, meta = train_text_model(*generate_vishing_corpus(), "Call transcript classifier", "Call is a vishing attempt")
    joblib.dump(art, MODELS / "voice_model.joblib")
    report["voice"] = meta
    print(f"  test AUC {meta['test']['roc_auc']}")

    (MODELS / "model_report.json").write_text(json.dumps(report, indent=2))
    print("Saved models and report to", MODELS)


if __name__ == "__main__":
    main()
