# Refiner ↔ Gulfstream Capstone Integration

**Version**: 1.1.0-Capstone  
**Status**: ✅ Ready for Integration  
**Date**: November 10, 2025

---

## Overview

Refiner now integrates seamlessly with the **Gulfstream Generative AI Capstone** project running in **WSL (Ubuntu-22.04)**. The integration allows you to:

- ✅ Analyze and refine 3D assets from capstone `input/` directory
- ✅ Process batch assets into capstone `outputs/` directory
- ✅ Convert paths between Windows, WSL, and UNC formats
- ✅ Validate capstone project structure
- ✅ List and process all input files with consistent parameters

---

## Architecture

```
Windows (Refiner)
    ↓
refiner_core/wsl_adapter.py (Path conversion & structure validation)
    ↓
refiner_core/capstone_cli.py (Capstone-specific commands)
    ↓
WSL (Ubuntu-22.04)
    ↓
~/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone/
    ├── input/          ← Read 3D assets from here
    ├── outputs/        ← Write refined assets here
    ├── backend/
    ├── scripts/
    └── models_cache/
```

---

## Installation & Setup

### 1. Prerequisites
- ✅ Windows with WSL (Ubuntu-22.04) installed
- ✅ Refiner installed on Windows (this directory)
- ✅ Python dependencies: `pip install -r requirements.txt`
- ✅ Capstone project accessible at `\\wsl.localhost\Ubuntu-22.04\home\corbino\Developer\REPO\2025Fall-Gulfstream-Generative-AI-Capstone`

### 2. Quick Setup
```bash
# In Windows (Refiner directory)
cd C:\Users\chard\OneDrive\Desktop\Refiner

# Test integration
python refiner_modern.py capstone status

# You should see capstone paths and available input files
```

### 3. Verify Connection
```bash
# List available input files from capstone
python refiner_modern.py capstone list-inputs

# Validate capstone project structure
python refiner_modern.py capstone status
```

---

## CLI Commands

### Capstone Status
```bash
python refiner_modern.py capstone status
```
**Output**: Shows capstone directory paths, validation status, and available input files.

### List Input Files
```bash
python refiner_modern.py capstone list-inputs
```
**Output**: Lists all 3D assets in capstone `input/` directory with file sizes.

### Process All Inputs
```bash
python refiner_modern.py capstone process-inputs \
  --method laplacian \
  --iterations 20 \
  --output-subdir refined_meshes
```
**Parameters**:
- `--method` — `taubin` (default) or `laplacian`
- `--iterations` — Number of smoothing iterations (default: 10)
- `--output-subdir` — Output directory within `outputs/` (default: `refined_meshes`)
- All standard Refiner options supported (see below)

**Output**: Processed assets saved to `outputs/<output-subdir>/`

### Convert Paths
```bash
python refiner_modern.py capstone convert-paths "C:\Users\chard\OneDrive\Desktop\Refiner"
```
**Output**: Shows converted paths in WSL and UNC formats.

---

## Advanced Options

All standard Refiner processing options work with capstone commands:

### Smoothing Options
```bash
python refiner_modern.py capstone process-inputs \
  --method laplacian \
  --iterations 30 \
  --lambda 0.6 \
  --nu -0.5
```

### Texture Processing
```bash
python refiner_modern.py capstone process-inputs \
  --smooth-textures \
  --texture-method bilateral \
  --bilateral-d 11 \
  --bilateral-sigma-color 100
```

### UV Unwrapping
```bash
python refiner_modern.py capstone process-inputs \
  --unwrap-uv-with-blender \
  --unwrap-attempts 3 \
  --unwrap-angle-limit 70
```

### Format Conversion Fallbacks
```bash
python refiner_modern.py capstone process-inputs \
  --blender-fallback \
  --assimp-fallback \
  --open3d-fallback
```

---

## Workflow Examples

### Example 1: Simple Refinement (Most Common)
```bash
# Process all capstone input files with default Taubin smoothing
python refiner_modern.py capstone process-inputs

# Output: C:\wsl.localhost\Ubuntu-22.04\home\corbino\Developer\REPO\...\outputs\refined_meshes\*_refined.glb
```

### Example 2: Aggressive Smoothing (High-Detail Reduction)
```bash
# Use Laplacian smoothing with 25 iterations
python refiner_modern.py capstone process-inputs \
  --method laplacian \
  --iterations 25 \
  --output-subdir aggressive_refined
```

### Example 3: With Texture Smoothing (OBJ Assets)
```bash
python refiner_modern.py capstone process-inputs \
  --smooth-textures \
  --texture-method bilateral \
  --bilateral-d 9 \
  --bilateral-sigma-color 75.0 \
  --output-subdir textures_refined
```

### Example 4: Full Pipeline (All Options)
```bash
python refiner_modern.py capstone process-inputs \
  --method laplacian \
  --iterations 20 \
  --smooth-textures \
  --texture-method bilateral \
  --bilateral-d 11 \
  --unwrap-uv-with-blender \
  --blender-fallback \
  --assimp-fallback \
  --pre-repair \
  --output-subdir full_pipeline
```

---

## Path Handling

### Understanding Path Formats

**Windows Path** (used in Windows CLI):
```
C:\Users\chard\OneDrive\Desktop\Refiner
```

**WSL Path** (used in WSL, Linux):
```
/mnt/c/Users/chard/OneDrive/Desktop/Refiner
```

**UNC Path** (cross-platform access):
```
\\wsl.localhost\Ubuntu-22.04\mnt\c\Users\chard\OneDrive\Desktop\Refiner
```

### Automatic Path Conversion
The adapter automatically detects and converts paths:

```bash
# Windows → WSL conversion (automatic)
C:\Users\chard\Desktop\model.obj → /mnt/c/Users/chard/Desktop/model.obj

# WSL → Windows conversion (automatic)
/home/corbino/project → \\wsl.localhost\Ubuntu-22.04\home\corbino\project
```

### Manual Path Conversion
```bash
# Convert Windows path to WSL
python refiner_modern.py capstone convert-paths "C:\path\to\file"

# Output:
# Input:          C:\path\to\file
# WSL path:       /mnt/c/path/to/file
# Windows (UNC):  \\wsl.localhost\Ubuntu-22.04\mnt\c\path\to\file
```

---

## Integration API (Python)

### Programmatic Access

```python
from refiner_core.wsl_adapter import RefinerCapstoneIntegration
from refiner_core.config import PipelineConfig

# Initialize integration
integration = RefinerCapstoneIntegration()

# Validate setup
is_valid, message = integration.validate()
print(f"Validation: {message}")

# Get input files
input_files = integration.get_capstone_input_files()
print(f"Found {len(input_files)} input files")

# Get output directory
output_dir = integration.get_capstone_output_dir('refined_meshes')
print(f"Output directory: {output_dir}")

# Process files
from refiner_core.pipeline import process_path

for input_file in input_files:
    result = process_path(
        input_path=input_file,
        outdir=output_dir,
        method='laplacian',
        iterations=20,
        # ... other parameters
    )
    print(f"Processed: {result}")
```

### Path Conversion API

```python
from refiner_core.wsl_adapter import WSLPathConverter

# Detect environment
env = WSLPathConverter.detect_environment()  # 'wsl', 'windows', or 'linux'

# Convert Windows → WSL
wsl_path = WSLPathConverter.to_wsl_path(r"C:\Users\chard\project")

# Convert WSL → Windows
win_path = WSLPathConverter.to_windows_path("/mnt/c/Users/chard/project")

# Convert to UNC (network path)
unc_path = WSLPathConverter.to_wsl_localhost_path("/home/corbino/project")
```

---

## Capstone Project Structure

The adapter expects this directory layout:

```
~/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone/
├── input/              ← Your 3D asset files here
├── outputs/            ← Refined assets written here
│   ├── refined_meshes/ ← Default subdirectory
│   └── ...
├── backend/            ← Capstone backend code
├── scripts/            ← Utility scripts
├── models_cache/       ← Model cache
├── submodules/         ← Git submodules
├── ui/                 ← UI code
├── docs/               ← Documentation
└── README.md
```

**Note**: If capstone structure differs, specify custom root:
```bash
python refiner_modern.py capstone status --capstone-root /path/to/capstone
```

---

## Supported Formats

### Input Formats
Refiner supports these 3D formats in capstone `input/`:
- ✅ OBJ (Wavefront)
- ✅ GLB (glTF 2.0 binary)
- ✅ GLTF (glTF 2.0 JSON)
- ✅ STL (stereolithography)
- ✅ PLY (polygon file format)
- ✅ CXPRJ (3D slicer projects)

### Output Format
By default, refined assets are exported as:
- **GLB** (glTF 2.0 binary) — Recommended for web/game engines

**File naming**: `<original-name>_refined.glb`

---

## Troubleshooting

### Issue: "Capstone root not found"
**Solution**: Verify capstone project exists:
```bash
python refiner_modern.py capstone status
```
If failed, specify custom path:
```bash
python refiner_modern.py capstone status --capstone-root /home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone
```

### Issue: "No input files found"
**Solution**: Add 3D files to capstone `input/` directory:
```bash
# Copy files from Windows
copy C:\your\models\*.obj \\wsl.localhost\Ubuntu-22.04\home\corbino\Developer\REPO\2025Fall-Gulfstream-Generative-AI-Capstone\input\
```

### Issue: "Blender not found" during processing
**Solution**: Either install Blender or skip fallback:
```bash
# Skip Blender fallback
python refiner_modern.py capstone process-inputs --no-blender-fallback

# Or specify Blender path
python refiner_modern.py capstone process-inputs --blender-exe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
```

### Issue: Permission denied on output directory
**Solution**: Check capstone output directory is writable:
```bash
# From WSL
chmod -R 755 ~/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone/outputs
```

### Issue: WSL path not found
**Solution**: Verify WSL is running and Ubuntu-22.04 is available:
```bash
wsl -l -v
# Should show: Ubuntu-22.04 Running

# If not running, start it:
wsl -d Ubuntu-22.04
```

---

## Performance Optimization

### Large Batch Processing
For processing 50+ assets:
```bash
# Use lower iterations for speed
python refiner_modern.py capstone process-inputs \
  --iterations 5 \
  --output-subdir fast_refine
```

### Memory-Intensive Processing
For high-polygon models (>500k vertices):
```bash
# Use adaptive smoothing with fewer iterations
python refiner_modern.py capstone process-inputs \
  --method laplacian \
  --iterations 10 \
  --output-subdir adaptive_refine
```

---

## Integration with Capstone Backend

### Feeding Refined Assets to Backend
Once assets are refined and stored in `outputs/refined_meshes/`:

```python
# From capstone backend code
from pathlib import Path

refined_dir = Path("/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone/outputs/refined_meshes")
refined_assets = sorted(refined_dir.glob("*.glb"))

for asset in refined_assets:
    # Process through your backend pipeline
    print(f"Processing: {asset}")
```

### Metadata Tracking
Each refined asset includes a JSON metadata file:
```json
{
  "source": "input/original_model.obj",
  "staged_at": "2025-11-10T12:34:56Z",
  "imported": false,
  "parameters": {
    "method": "laplacian",
    "iterations": 20
  }
}
```

---

## Advanced: Custom Capstone Root

Set the capstone root via environment variable:

```bash
# Windows PowerShell
$env:CAPSTONE_ROOT = "\\wsl.localhost\Ubuntu-22.04\home\corbino\Developer\REPO\2025Fall-Gulfstream-Generative-AI-Capstone"
python refiner_modern.py capstone status

# Or Linux/WSL
export CAPSTONE_ROOT=/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone
```

---

## Next Steps

1. ✅ [**Quick Start**] Run `python refiner_modern.py capstone status` to verify setup
2. ✅ [**List Assets**] Run `python refiner_modern.py capstone list-inputs` to see available files
3. ✅ [**Process Assets**] Run `python refiner_modern.py capstone process-inputs` to refine them
4. ✅ [**Integrate with Backend**] Use refined assets from `outputs/refined_meshes/` in your pipeline

---

## Support

For issues or questions:
1. Check **Troubleshooting** section above
2. Review **QUICK_REFERENCE.md** for general Refiner usage
3. Review **PROJECT_STATUS.md** for complete capabilities
4. Check WSL connectivity: `wsl --list --verbose`

---

**Status**: ✅ Ready for Capstone Integration  
**Maintained**: Refiner Development Team  
**Last Updated**: November 10, 2025
