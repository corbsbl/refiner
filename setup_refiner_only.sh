#!/bin/bash
# Refiner + Capstone Integration Setup (Non-root version)
# This sets up Refiner venv and validates capstone project
# Run from Windows: wsl bash setup_refiner_only.sh

set -e

# Configuration
REFINER_PATH="/mnt/c/Users/chard/OneDrive/Desktop/Refiner"
CAPSTONE_PATH="/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone"

echo "======================================="
echo "Refiner WSL Setup"
echo "======================================="
echo ""

# Step 1: Create venv
echo "[1/3] Creating Python virtual environment..."
cd "$REFINER_PATH"
python3 -m venv .venv_wsl
echo "✓ Virtual environment created"

# Step 2: Install dependencies
echo ""
echo "[2/3] Installing Refiner dependencies..."
source "$REFINER_PATH/.venv_wsl/bin/activate"
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

# Step 3: Verify capstone access
echo ""
echo "[3/3] Verifying capstone project access..."
if [ -d "$CAPSTONE_PATH" ]; then
    echo "✓ Capstone root found: $CAPSTONE_PATH"
    
    if [ -d "$CAPSTONE_PATH/input" ]; then
        INPUT_COUNT=$(ls -1 "$CAPSTONE_PATH/input" 2>/dev/null | wc -l)
        echo "  ✓ Input directory: $INPUT_COUNT files/folders"
    fi
    
    if [ -d "$CAPSTONE_PATH/outputs" ]; then
        echo "  ✓ Output directory: ready for writing"
    fi
else
    echo "✗ Capstone root NOT found at $CAPSTONE_PATH"
    exit 1
fi

echo ""
echo "======================================="
echo "Setup Complete!"
echo "======================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Test Refiner in WSL:"
echo "   wsl bash -c 'source /mnt/c/Users/chard/OneDrive/Desktop/Refiner/.venv_wsl/bin/activate && python /mnt/c/Users/chard/OneDrive/Desktop/Refiner/refiner_modern.py capstone status'"
echo ""
echo "2. Or use PowerShell wrapper from Windows:"
echo "   cd C:\\Users\\chard\\OneDrive\\Desktop\\Refiner"
echo "   .\\refiner_wsl.ps1 capstone status"
echo ""
