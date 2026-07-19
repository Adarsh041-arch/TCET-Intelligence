@echo off
echo ========================================
echo TCET Chatbot - Setup Script
echo ========================================
echo.

echo [1/3] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    exit /b 1
)

echo [2/3] Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
)

echo Installing Playwright browser...
playwright install chromium
if errorlevel 1 (
    echo Warning: Failed to install Playwright browser. PDF generation may fail.
)

echo [3/3] Downloading Ollama model...
echo Please ensure Ollama is installed and running
echo Run: ollama pull qwen2.5:3b
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start Ollama: ollama serve
echo 2. Pull model: ollama pull qwen2.5:3b
echo 3. Start backend: python run_backend.bat
echo 4. Start frontend: python run_frontend.bat
echo.
pause
