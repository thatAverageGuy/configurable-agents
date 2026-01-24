@echo off
REM Setup script for Windows - Creates venv and installs dependencies

echo ========================================
echo Configurable Agents - Development Setup
echo ========================================
echo.

REM Check if virtual environment exists
if exist .venv\Scripts\activate.bat (
    echo [INFO] Virtual environment already exists at .venv
    echo [INFO] Skipping venv creation...
) else (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

echo.
echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo [3/3] Installing dependencies...
python -m pip install --upgrade pip
pip install -e ".[dev]"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To activate the virtual environment:
echo   .venv\Scripts\activate
echo.
echo To run tests:
echo   pytest tests/ -v
echo.
echo To deactivate:
echo   deactivate
echo.
