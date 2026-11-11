# Khởi chạy Backend FastAPI
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Khởi động Backend - Traffic Accident Detection" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "backend"
if (Test-Path ".\venv\Scripts\python.exe") {
    .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
