#!/bin/bash
# Complete Refiner + Capstone Ecosystem Setup for WSL
# This script sets up everything needed to run Refiner with the capstone project
# Run from Windows: wsl bash setup_complete_ecosystem.sh

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Refiner + Capstone Ecosystem Setup${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Configuration
REFINER_PATH="/mnt/c/Users/chard/OneDrive/Desktop/Refiner"
CAPSTONE_PATH="/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone"
STEP=1

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}[$STEP/8] $1${NC}"
    ((STEP++))
}

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# STEP 1: System Dependencies
# =============================================================================
print_section "Installing System Dependencies"

echo "Updating package lists..."
sudo apt update -qq

echo "Installing core dependencies..."
sudo apt install -y \
  python3.10 python3.10-venv python3-pip \
  git curl build-essential \
  libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
  ffmpeg pkg-config \
  2>&1 | grep -v "Setting up" | tail -5

echo -e "${GREEN}✓ System dependencies installed${NC}"

# =============================================================================
# STEP 2: Python 3.10 Venv Setup
# =============================================================================
print_section "Setting up Python 3.10 Virtual Environment"

if [ ! -d "$REFINER_PATH/.venv_wsl" ]; then
    echo "Creating virtual environment..."
    cd "$REFINER_PATH"
    python3.10 -m venv .venv_wsl
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}✓ Virtual environment already exists${NC}"
fi

# =============================================================================
# STEP 3: Refiner Dependencies
# =============================================================================
print_section "Installing Refiner Dependencies"

source "$REFINER_PATH/.venv_wsl/bin/activate"

echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel 2>&1 | tail -3

echo "Installing Refiner requirements..."
cd "$REFINER_PATH"
pip install -r requirements.txt 2>&1 | grep -E "Successfully|Collecting|already"

echo -e "${GREEN}✓ Refiner dependencies installed${NC}"

# =============================================================================
# STEP 4: CUDA Toolkit (Optional - Check if available)
# =============================================================================
print_section "Checking CUDA Availability"

if command_exists nvidia-smi; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | sed 's/^/  GPU: /'
    CUDA_AVAILABLE=true
else
    echo -e "${YELLOW}! NVIDIA GPU not detected (optional for backend)${NC}"
    echo "  If you have NVIDIA GPU, install CUDA Toolkit from:"
    echo "  https://docs.nvidia.com/cuda/wsl-user-guide/index.html"
    CUDA_AVAILABLE=false
fi

# =============================================================================
# STEP 5: Capstone Backend Setup
# =============================================================================
print_section "Setting up Capstone Backend"

if [ -d "$CAPSTONE_PATH/backend" ]; then
    echo "Creating capstone backend venv..."
    cd "$CAPSTONE_PATH/backend"
    
    if [ ! -d ".venv" ]; then
        python3.10 -m venv .venv
        source .venv/bin/activate
        
        echo "Upgrading pip..."
        pip install --upgrade pip setuptools wheel 2>&1 | tail -1
        
        echo "Installing capstone backend requirements..."
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt 2>&1 | grep -E "Successfully|Collecting" | head -10
        else
            echo -e "${YELLOW}! Backend requirements.txt not found${NC}"
        fi
    else
        source .venv/bin/activate
        echo -e "${YELLOW}✓ Backend venv already exists${NC}"
    fi
    
    echo -e "${GREEN}✓ Capstone backend configured${NC}"
else
    echo -e "${YELLOW}! Capstone backend directory not found${NC}"
fi

# =============================================================================
# STEP 6: Node.js & UI Setup
# =============================================================================
print_section "Setting up UI (Node.js + React)"

if command_exists nvm; then
    echo "NVM already installed"
    NVM_DIR="$HOME/.nvm"
    source "$NVM_DIR/nvm.sh"
else
    echo "Installing NVM (Node Version Manager)..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
fi

echo "Installing Node.js 18..."
nvm install 18 2>&1 | tail -3
nvm use 18
nvm alias default 18

echo "Verifying Node/npm..."
node -v | sed 's/^/  Node: /'
npm -v | sed 's/^/  npm: /'

if [ -d "$CAPSTONE_PATH/ui" ]; then
    echo "Installing UI dependencies..."
    cd "$CAPSTONE_PATH/ui"
    npm install 2>&1 | tail -5
    echo -e "${GREEN}✓ UI configured${NC}"
else
    echo -e "${YELLOW}! Capstone UI directory not found${NC}"
fi

# =============================================================================
# STEP 7: Validation & Status
# =============================================================================
print_section "Validating Setup"

echo "Checking installations..."

# Refiner
source "$REFINER_PATH/.venv_wsl/bin/activate" 2>/dev/null
python3 -c "import trimesh, numpy, cv2; print('  ✓ Refiner dependencies OK')" 2>/dev/null || echo "  ⚠ Refiner: Some packages may be missing"

# Check capstone paths
[ -d "$CAPSTONE_PATH/input" ] && echo "  ✓ Capstone input/ directory found"
[ -d "$CAPSTONE_PATH/outputs" ] && echo "  ✓ Capstone outputs/ directory found"
[ -d "$CAPSTONE_PATH/backend" ] && echo "  ✓ Capstone backend/ directory found"
[ -d "$CAPSTONE_PATH/ui" ] && echo "  ✓ Capstone ui/ directory found"

# =============================================================================
# STEP 8: Quick Start Guide
# =============================================================================
print_section "Setup Complete!"

echo ""
echo -e "${GREEN}=== Quick Start Guide ===${NC}"
echo ""
echo -e "${YELLOW}1. Check Refiner in WSL:${NC}"
echo "   wsl bash -c 'source /mnt/c/Users/chard/OneDrive/Desktop/Refiner/.venv_wsl/bin/activate && python /mnt/c/Users/chard/OneDrive/Desktop/Refiner/refiner_modern.py capstone status'"
echo ""
echo -e "${YELLOW}2. From Windows (using PowerShell wrapper):${NC}"
echo "   cd C:\\Users\\chard\\OneDrive\\Desktop\\Refiner"
echo "   .\\refiner_wsl.ps1 capstone status"
echo ""
echo -e "${YELLOW}3. Process capstone inputs:${NC}"
echo "   .\\refiner_wsl.ps1 capstone process-inputs --method laplacian --iterations 20"
echo ""
if [ "$CUDA_AVAILABLE" = true ]; then
    echo -e "${YELLOW}4. Start capstone backend (with GPU support):${NC}"
    echo "   cd $CAPSTONE_PATH/backend"
    echo "   source .venv/bin/activate"
    echo "   python -m uvicorn main:app --reload"
    echo ""
    echo -e "${YELLOW}5. Start capstone UI:${NC}"
    echo "   cd $CAPSTONE_PATH/ui"
    echo "   npm start"
    echo ""
fi
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
