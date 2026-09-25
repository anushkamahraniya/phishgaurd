"""PhishGuard ML API.  Run from backend/:  .venv\\Scripts\\uvicorn app.main:app --reload"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

import qrcode
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ml.features import EMP_COLS
from .content import MODULES, TEMPLATES
from .checker import get_checker
from .engine import get_engine

app = FastAPI(title="PhishGuard ML", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

Modality = Literal["text", "image", "url", "audio"]


@app.on_event("startup")
def _startup():
    get_engine()
    get_checker()


# ---------------------------------------------------------------- dashboard
@app.get("/api/dashboard")
def dashboard():
    return get_engine().dashboard()


# ---------------------------------------------------------------- employees
@app.get("/api/employees")
def employees(search: str = "", dept: str = "All", level: str = "All", weakness: str = "All",
              sort: str = "risk", order: str = "desc", page: int = 1, size: int = Query(25, le=200)):
    return get_engine().employees(search, dept, level, weakness, sort, order, page, size)


@app.get("/api/employees/{emp_id}")
def employee(emp_id: str):
    e = get_engine()
    try:
        return e.employee_row(e.df.loc[e.get_index(emp_id)])
    except KeyError:
        raise HTTPException(404, f"No employee with ID {emp_id}")


# ---------------------------------------------------------------------- XAI
@app.get("/api/xai/employee/{emp_id}")
def explain_employee(emp_id: str):
    try:
        return get_engine().explain_employee(emp_id)
    except KeyError:
        raise HTTPException(404, f"No employee with ID {emp_id}")


class Features(BaseModel):
    url_fail_rate: float = Field(ge=0, le=100)
    text_fail_rate: float = Field(ge=0, le=100)
    image_fail_rate: float = Field(ge=0, le=100)
    audio_fail_rate: float = Field(ge=0, le=100)
    avg_response_sec: float = Field(ge=1, le=1000)
    report_rate: float = Field(ge=0, le=100)
    training_completed: float = Field(ge=0, le=10)
    days_since_training: float = Field(ge=0, le=720)
    mfa_enabled: float = Field(ge=0, le=1)
    after_hours_pct: float = Field(ge=0, le=100)
    seniority: float = Field(ge=0, le=2)
    tenure_years: float = Field(ge=0, le=40)


@app.post("/api/xai/predict")
def predict(f: Features):
    return get_engine().explain_vector(f.model_dump())


@app.get("/api/xai/global")
def global_xai():
    return get_engine().global_explanations()


@app.get("/api/xai/high-risk")
def high_risk(n: int = 12):
    return get_engine().high_risk(n)


@app.get("/api/model/report")
def model_report():
    r = get_engine().report
    return {k: {kk: vv for kk, vv in v.items() if kk != "beeswarm"} for k, v in r.items()}


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    kind: Literal["email", "voice"] = "email"


@app.post("/api/analyze/text")
def analyze_text(body: TextIn):
    return get_engine().analyze_text(body.text, body.kind)


# ------------------------------------------------------- check a message
class CheckTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.post("/api/check")
def check_text(body: CheckTextIn):
    return get_checker().check_text(body.text)


MAX_UPLOAD = 20 * 1024 * 1024


@app.post("/api/check/file")
async def check_file(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is too big. Use one under 20 MB.")
    return get_checker().check_file(data, file.filename, file.content_type)


# ---------------------------------------------------------------- campaigns
@app.get("/api/templates")
def templates():
    return TEMPLATES


@app.get("/api/campaigns")
def campaigns():
    return get_engine().campaigns


@app.get("/api/campaigns/forecast")
def forecast(modality: Modality, dept: str = "All", difficulty: str = "Medium"):
    return get_engine().campaign_forecast(modality, dept, difficulty)


class CampaignIn(BaseModel):
    name: str = ""
    modality: Modality
    template_id: str
    dept: str = "All"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"


@app.post("/api/campaigns")
def launch(c: CampaignIn):
    return get_engine().launch_campaign(c.name, c.modality, c.template_id, c.dept, c.difficulty)


@app.get("/api/sim/qr.png")
def qr_png(request: Request, c: str = "demo"):
    """QR code for the image-modality preview. It encodes this app's own training landing page."""
    img = qrcode.make(f"{str(request.base_url).rstrip('/')}/sim/landing?c={c}", box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.get("/sim/landing", response_class=HTMLResponse)
def landing(c: str = ""):
    return """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>This was a phishing simulation</title>
<body style="font-family:system-ui;background:#0b1220;color:#e2e8f0;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px">
<main style="max-width:520px;background:#111a2b;border:1px solid #1e293b;border-radius:14px;padding:28px">
<p style="color:#22d3ee;font:600 12px monospace;letter-spacing:.08em;text-transform:uppercase">PhishGuard ML - security awareness</p>
<h1 style="margin:.2em 0 .5em;font-size:24px">This was a simulated phishing test</h1>
<p style="color:#94a3b8;line-height:1.6">No data was collected and nothing is wrong with your account. This message was sent by your security team to help you practise spotting phishing.</p>
<p style="color:#94a3b8;line-height:1.6">A short training module matched to what just happened has been added to your Training Portal.</p>
</main></body>"""


# ----------------------------------------------------------------- training
@app.get("/api/modules")
def modules():
    return MODULES


@app.post("/api/training/auto-assign")
def auto_assign():
    out = get_engine().auto_assign()
    return {"assigned": len(out), "assignments": out[:25]}


@app.get("/api/training/{emp_id}")
def training(emp_id: str):
    try:
        return get_engine().training(emp_id)
    except KeyError:
        raise HTTPException(404, f"No employee with ID {emp_id}")


class CheckIn(BaseModel):
    question_id: str
    answer: str
    emp_id: str | None = None


@app.post("/api/training/check")
def check(body: CheckIn):
    try:
        return get_engine().check_answer(body.question_id, body.answer, body.emp_id)
    except KeyError:
        raise HTTPException(404, "Unknown question or employee")


class QuizIn(BaseModel):
    answers: dict[str, str]


@app.post("/api/training/{emp_id}/submit")
def submit(emp_id: str, body: QuizIn):
    try:
        return get_engine().submit_quiz(emp_id, body.answers)
    except KeyError:
        raise HTTPException(404, f"No employee with ID {emp_id}")


@app.post("/api/reset")
def reset():
    get_engine().reset()
    return {"ok": True}


@app.get("/api/meta")
def meta():
    return {"features": EMP_COLS}


# ------------------------------------------------------- serve built frontend
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
