@echo off
title Backend - Traffic Accident Detection
echo =================================================
echo  Khoi dong Backend - Traffic Accident Detection
echo =================================================
set PYTHONPATH=backend
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
pause
