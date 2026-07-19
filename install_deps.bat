@echo off
echo ========================================
echo Installing Python Dependencies
echo ========================================
echo.

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

echo.
echo Installing packages...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Installing Playwright browser...
playwright install chromium

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
pause
