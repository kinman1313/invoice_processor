@echo off
REM Quick setup script for Invoice Processing Agent on Windows

echo.
echo 🚀 Invoice Processing Agent - Setup Script
echo ==========================================
echo.

REM Check Python
echo ✓ Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python not found. Please install Python 3.8+
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version') do set "python_version=%%i"
    echo   Found: %python_version%
)

REM Create virtual environment
echo.
echo ✓ Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo   Created: venv\
) else (
    echo   Already exists: venv\
)

REM Activate virtual environment
echo.
echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat
echo   Activated

REM Install dependencies
echo.
echo ✓ Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo   ⚠️  Some packages may have failed. Check requirements.txt
) else (
    echo   Installed from requirements.txt
)

REM Setup .env file
echo.
echo ✓ Setting up configuration...
if not exist ".env" (
    copy .env.example .env >nul
    echo   Created: .env (edit this file with your API key)
) else (
    echo   Already exists: .env
)

REM Generate sample invoices
echo.
echo ✓ Generating sample invoices...
python generate_samples.py >nul 2>&1
if errorlevel 1 (
    echo   ⚠️  Could not generate samples. Check ReportLab installation.
) else (
    echo   Created 5 sample invoices in sample_invoices\
)

REM Summary
echo.
echo ==========================================
echo ✅ Setup Complete!
echo.
echo Next steps:
echo.
echo 1. Edit .env and add your Anthropic API key:
echo    ANTHROPIC_API_KEY=sk-ant-...
echo.
echo 2. Start the web interface:
echo    streamlit run app.py
echo.
echo    Or test from command line:
echo    python invoice_agent.py sample_invoices\invoice_clean.pdf
echo.
echo ==========================================
echo.
pause
