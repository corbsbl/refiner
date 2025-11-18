# Refiner WSL Launcher
# Usage: .\refiner_wsl.ps1 capstone status
# Usage: .\refiner_wsl.ps1 capstone list-inputs
# Usage: .\refiner_wsl.ps1 capstone process-inputs --method laplacian --iterations 20

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RefinerArgs
)

$RefinerPath = "C:\Users\chard\OneDrive\Desktop\Refiner"
$VenvPath = ".venv_wsl"
$VenvBinPath = "$RefinerPath\$VenvPath\Scripts\python.exe"

# Check if venv exists
if (-not (Test-Path $VenvBinPath)) {
    Write-Host "Setting up Refiner in WSL environment..." -ForegroundColor Yellow
    Write-Host ""
    
    # Run setup script in WSL
    wsl bash /mnt/c/Users/chard/OneDrive/Desktop/Refiner/setup_wsl.sh
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WSL setup failed!" -ForegroundColor Red
        exit 1
    }
}

# Prepare command for WSL
$wsCommand = @"
source /mnt/c/Users/chard/OneDrive/Desktop/Refiner/.venv_wsl/bin/activate && `
cd /mnt/c/Users/chard/OneDrive/Desktop/Refiner && `
python refiner_modern.py $($RefinerArgs -join ' ')
"@

Write-Host "=== Running Refiner in WSL ===" -ForegroundColor Cyan
Write-Host ""

# Run in WSL
wsl bash -c $wsCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Command failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
