# Refiner → Unreal Integration Plan

## 1. Objective
- Guarantee every 3D asset passes through the Refiner pipeline before landing in Unreal Engine.
- Automate the conversion, cleanup, smoothing, and export so that Unreal receives ready-to-import assets.
- Preserve traceability: every Unreal asset should be linked back to its input file and the refiner parameters used.

## 2. Current Pipeline Snapshot
- **Supported inputs**: OBJ, GLB/GLTF, STL, Cura/Cricut CXPRJ (with embedded SVG/STL extraction).
- **Core processing**: pre-repair (dedup/weld/degenerate removal), adaptive smoothing (Taubin/Laplacian), optional symmetry gating/repair, UV auto-unwrap via Blender, texture smoothing (OBJ).
- **Batch tooling**: analyze-only mode, job manifests, API output folders, per-mesh metrics, CLI flag coverage.
- **Recent enhancements**: CXPRJ → mesh converter, STL ingestion, Laplacian smoothing presets, aggressive smoothing runbooks (gus assets).

## 3. Unreal Target Workflow (Non-Negotiable)
```
Raw asset(s) → Refiner CLI → Unreal project Content/
```
- Refiner continues to be the central gate.
- Export step must deposit results under `<UnrealProject>/Content/<ConfiguredFolder>/`.
- Unreal Editor should auto-detect new assets or scripts should trigger import via Python API.

## 4. Export Format Research
| Format | Unreal Support | Notes |
|--------|----------------|-------|
| **FBX** | Native, mature importer. Supports static/skeletal meshes, materials, LODs. Recommended default. | Requires FBX SDK or Blender/Assimp bridge. Handles smoothing groups. |
| **glTF/GLB** | Supported via official glTF importer plugin (UE 4.27+, 5.x). Good for PBR materials. | Plugin must be enabled. Less mature than FBX for animation. |
| **USD/USDZ** | First-class in UE 5.x. Best for large pipelines. | Heavier dependency; overkill for initial integration. |
| **OBJ** | Basic static mesh import. No materials/UV metadata. | Already produced, but Unreal requires manual import. |

**Recommended**: Export FBX for Unreal. Provide optional GLB for pipelines that enable the plugin.

## 5. Export Implementation Options
1. **Trimesh/Assimp FBX export**
   - Use `pyassimp` or command-line `assimp export` to convert OBJ → FBX post-refinement.
   - Pros: Lightweight, no Blender dependency. Cons: less control over materials.

2. **Blender headless exporter**
   - Run Blender with `--background` script: import refined OBJ/GLB, apply scale, export FBX with correct settings.
   - Pros: Rich control (axis, scale, smoothing). Cons: requires Blender installation.

3. **Unreal Python direct import (no pre-export)**
   - Launch Unreal Editor with command-line Python to import OBJ/GLB directly.
   - Pros: Fewer external tools. Cons: requires Unreal Editor headless session; slower for batch.

**Decision**: Start with Blender headless export to FBX (option 2). Keeps pipeline consistent with existing Blender-based UV unwrap.

## 6. Proposed Architecture
```
refiner_core/
  exporters.py        # Add export_fbx, export_glb helpers
  unreal_bridge.py    # New module controlling UE handoff
  cli.py              # Add --unreal-project, --unreal-folder flags
  pipeline.py         # Call export_to_unreal if flags provided
```

### Steps during `process_file`
1. Run existing refinement workflow.
2. After base export, detect Unreal flags.
3. Invoke `export_to_unreal(refined_path, unreal_project_dir, target_folder)`.
4. `export_to_unreal` handles:
   - Ensuring `<project>/Content/<folder>` exists.
   - Converting mesh to FBX (via Blender script).
   - Writing metadata JSON (`<asset>.refiner.json`) with provenance.
   - Optional: copying GLB for future use.

### Metadata schema (`*.refiner.json`)
```json
{
  "source": "input/gus_from_cxprj.stl",
  "refiner": {
    "method": "laplacian",
    "iterations": 20,
    "pre_repair": true,
    "timestamp": "2025-10-24T14:12:33Z"
  },
  "unreal": {
    "project": "C:/Projects/MyGame",
    "content_subdir": "Meshes/Refined",
    "export_format": "fbx"
  }
}
```

## 7. Automation Hooks
- **Optional Unreal Python**: provide script template to auto-import newly staged FBX files:
  ```python
  import unreal
  task = unreal.AssetImportTask()
  task.filename = "C:/Projects/MyGame/Content/Meshes/Refined/gus_refined.fbx"
  task.destination_path = "/Game/Meshes/Refined"
  task.automated = True
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  ```
- **Command-line trigger**: `UnrealEditor-Cmd.exe <uproject> -run=pythonscript [script.py]` for unattended imports.

## 8. Outstanding Work
1. **FBX export helper** (Blender or Assimp) with axis/scale options. *(In progress discussion)*
2. **CLI extensions**: `--unreal-project`, `--unreal-assets-folder`, `--unreal-format {fbx,glb}`.
3. **Unreal project validation** (check `.uproject`, ensure Content folder present).
4. **Metadata writer** for provenance tracking.
5. **Documentation update** (README + usage examples).
6. **Testing**
   - Small mesh smoke test (simple cube)
   - Mid-size mesh (gus)
   - Batch directory
   - Error handling (missing Blender, invalid project path)
7. **Future enhancements**
   - Auto-generate collision meshes.
   - Optional LOD generation via `trimesh.simplify_quadratic_decimation`.
   - Material template exports (e.g., write base UE material setup).

## 9. Summary
We have a clear path to ensure every asset is refined before entering Unreal. By adding FBX export and project staging, the refiner becomes the gatekeeper for geometry quality, while Unreal receives consistent, ready-to-use assets with traceable metadata. Next steps focus on implementing the export bridge, CLI flags, and documentation so the workflow can be executed with a single command.
