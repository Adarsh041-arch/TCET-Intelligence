@echo off
echo Starting TCET Chatbot Backend Server...
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo Backend will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
