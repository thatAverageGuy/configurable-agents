#!/bin/bash
# Setup script for Unix-like systems - Creates venv and installs dependencies

set -e  # Exit on error

echo "========================================"
echo "Configurable Agents - Development Setup"
echo "========================================"
echo

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "[INFO] Virtual environment already exists at .venv"
    echo "[INFO] Skipping venv creation..."
else
    echo "[1/3] Creating virtual environment..."
    python -m venv .venv
    echo "[SUCCESS] Virtual environment created"
fi

echo
echo "[2/3] Activating virtual environment..."
# Handle both Unix (bin) and Windows (Scripts) activation paths
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "[ERROR] Could not find activation script"
    exit 1
fi

echo
echo "[3/3] Installing dependencies..."
python -m pip install --upgrade pip
pip install -e ".[dev]"

echo
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo
echo "To run tests:"
echo "  pytest tests/ -v"
echo
echo "To deactivate:"
echo "  deactivate"
echo
