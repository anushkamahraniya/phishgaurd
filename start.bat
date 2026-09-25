@echo off
REM Start PhishGuard, then open http://localhost:8000
cd /d "%~dp0backend"
if not exist models\risk_model.joblib .venv\Scripts\python -m ml.train
REM Scam checkers need the Kaggle data in backend\data\kaggle (see ml\train_checkers.py)
if not exist models\check_links.joblib .venv\Scripts\python -m ml.train_checkers
start "" http://localhost:8000
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
