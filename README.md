# Refiner: Mesh and Texture Smoother

**Version**: 1.1.0 (Optimized)  
**Status**: ✅ Production Ready

> 🎯 **NEW**: Modern CLI with subcommands available! Use `python refiner_modern.py` for improved architecture and better organization. See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for examples.


Overview

- Smooths vertices of 3D models (OBJ/GLB/GLTF; FBX is skipped with guidance).
- Optionally smooths OBJ diffuse textures (map_Kd in MTL) using edge-preserving filters.
-- Analyzer reports symmetry metrics (Chamfer-based) for team review; automatic symmetry replication has been removed.
 - Optional Blender fallback: if a GLB/GLTF loads as an empty scene, try headless Blender to convert to OBJ and retry.
 - Optional Assimp and Open3D fallbacks; an inspect-only mode to debug GLB/GLTF contents.

What it does

- Mesh smoothing: Taubin (default) or Laplacian smoothing using trimesh.
- Texture smoothing: bilateral (default) or Gaussian blur applied to diffuse textures referenced by OBJ MTL.
 - Symmetry replication has been removed from the automated pipeline; the analyzer reports symmetry scores for manual review.
 - Blender fallback: imports GLB/GLTF/FBX via Blender and exports an OBJ to unblock processing when other loaders fail.

Setup (Windows PowerShell)

1) Create/activate a Python 3.10+ environment (recommended but optional):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2) Install dependencies:

```powershell
pip install -r requirements.txt
```

Basic usage

Place input files/folders in the `input` directory or anywhere on disk. Outputs go to `output` by default.

```powershell
python refiner.py input
```

Examples

- Smooth a single OBJ and its diffuse textures:

```powershell
python refiner.py .\input\model.obj --smooth-textures
```

- Process a directory recursively (OBJ/GLB/GLTF). FBX files are skipped with a message:

```powershell
python refiner.py .\input
```

- Use Laplacian smoothing with 20 iterations:

```powershell
python refiner.py .\input\mesh.glb --method laplacian --iterations 20
```

- Stronger bilateral texture smoothing:
 - Use Blender fallback if GLB loads empty:

```powershell
python refiner.py .\input\chair.glb --blender-fallback
```

 - Specify Blender path explicitly (if not on PATH):
 - Try all fallbacks and inspect a GLB:

```powershell
python refiner.py .\input\chair.glb --inspect-only
python refiner.py .\input\chair.glb --assimp-fallback --open3d-fallback --blender-fallback
```

```powershell
python refiner.py .\input\chair.glb --blender-fallback --blender-exe "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

 - Symmetry repair on the X axis, prefer positive side:
```powershell
python refiner.py .\input\model.obj --smooth-textures --bilateral-d 11 --bilateral-sigma-color 100 --bilateral-sigma-space 100
```

```powershell
python refiner.py .\input\model.obj --smooth-textures --bilateral-d 11 --bilateral-sigma-color 100 --bilateral-sigma-space 100
```

Notes on FBX

- This tool does not process FBX directly. Convert FBX to GLB/OBJ first (e.g., with Blender) and rerun.

Outputs

- Refined meshes are saved to the output folder with `_refined` suffix, preserving original format.
- When texture smoothing is enabled for OBJ, updated texture files are written next to the exported OBJ/MTL with `_smoothed` in the filename, and the MTL is updated accordingly.

Documentation

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — Quick start guide with common workflows and examples
- **[OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md)** — Technical details on all optimizations (v1.1.0)
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** — Complete project status and capabilities
- **[FILE_SUMMARY.md](FILE_SUMMARY.md)** — Summary of all files created/modified
- **[docs/SPECIFICATION.md](docs/SPECIFICATION.md)** — Full architecture and implementation details
- **[docs/unreal_integration_guide.md](docs/unreal_integration_guide.md)** — Unreal Engine integration workflows

Troubleshooting

- If imports fail, ensure dependencies are installed: `pip install -r requirements.txt`.
- For large models, increase iterations gradually and keep Taubin defaults to preserve volume.
- If textures don't change, check that your OBJ references them in the MTL via `map_Kd`.
- For Unreal project validation issues, ensure `.uproject` path is correct and `Content/` folder exists and is writable.

