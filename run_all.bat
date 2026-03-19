@echo off
echo ========================================
echo TCET Chatbot - Starting All Services
echo ========================================
echo.

start "TCET Backend" cmd /c "call run_backend.bat"

timeout /t 3 /nobreak >nul

start "TCET Frontend" cmd /c "call run_frontend.bat"

echo.
echo ========================================
echo Services Started!
echo ========================================
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:8501
echo.
echo Default Admin: admin / admin123
echo ========================================
echo.
pause
