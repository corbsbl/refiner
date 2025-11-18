#!/bin/bash
# Setup Refiner in WSL environment
# Run this INSIDE WSL: wsl bash setup_wsl.sh

set -e

REFINER_PATH="/mnt/c/Users/chard/OneDrive/Desktop/Refiner"
CAPSTONE_PATH="/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone"

echo "=== Refiner WSL Setup ==="
echo ""
echo "Refiner path:  $REFINER_PATH"
echo "Capstone path: $CAPSTONE_PATH"
echo ""

# Check if venv exists
if [ ! -d "$REFINER_PATH/.venv_wsl" ]; then
    echo "[1/4] Creating Python virtual environment..."
    cd "$REFINER_PATH"
    python3 -m venv .venv_wsl
    echo "✓ Virtual environment created"
else
    echo "[1/4] Virtual environment already exists"
fi

echo ""
echo "[2/4] Activating virtual environment..."
source "$REFINER_PATH/.venv_wsl/bin/activate"
echo "✓ Virtual environment activated"

echo ""
echo "[3/4] Installing Refiner dependencies..."
cd "$REFINER_PATH"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo "✓ Dependencies installed"

echo ""
echo "[4/4] Verifying installation..."
python3 -c "import open3d, trimesh, numpy; print('✓ All dependencies available')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use Refiner from WSL:"
echo "  wsl source /mnt/c/Users/chard/OneDrive/Desktop/Refiner/.venv_wsl/bin/activate"
echo "  cd /mnt/c/Users/chard/OneDrive/Desktop/Refiner"
echo "  python refiner_modern.py capstone status"
echo ""
