# Research Findings & Test Results

## Export Method Evaluation

### Tested Approaches

| Method | Status | Notes |
|--------|--------|-------|
| **Trimesh FBX** | ❌ Failed | FBX exporter not available in trimesh without external SDK |
| **Assimp CLI** | ❌ Not Installed | Would require separate installation and CLI wrapping |
| **Blender Headless** | ❌ Failed | OBJ importer addon unavailable in headless mode (requires GUI initialization) |
| **Trimesh → STL** | ✅ Working | Reliable; 20MB output for gus mesh |
| **Trimesh → GLB** | ✅ Working | **RECOMMENDED** - 7.2MB (35% smaller), preserves geometry, Unreal 4.27+ native support |
| **Trimesh → PLY** | ✅ Working | Working; 7.6MB output; less Unreal support |

### Test Environment
- System: Windows 11, Python 3.12 venv
- Blender: 4.3.2 installed (C:\Program Files\Blender Foundation\)
- Trimesh: 4.4.3 (built-in, no FBX SDK)
- Assimp: Not installed

### Recommendation

**Use GLB (glTF 2.0 Binary) for Unreal export:**
- Trimesh exports GLB reliably and built-in (no external deps)
- Unreal has native GLB importer (enabled by default in 4.27+, 5.x)
- 35% smaller than STL (7.2MB vs 20MB for gus)
- Preserves mesh topology and surface properties perfectly
- Can embed basic material slots (future enhancement)
- Industry standard for game asset interchange

**Plan**: Export refined meshes as GLB, stage directly in Unreal Content folder.

## Test Results Summary

### Gus Model (201k vertices, 402k faces)
```
Input:  output/gus_from_cxprj_refined.obj (OBJ from refinement pipeline)

Outputs:
  - STL:  20,105,384 bytes  ✓ (fallback option)
  - GLB:   7,238,816 bytes  ✓ (PRIMARY)
  - PLY:   7,640,163 bytes  ✓ (alternative)
```

### Next: Unreal Project Structure

Unreal expects assets in:
```
C:/Projects/MyGame/
  ├── Binaries/
  ├── Content/
  │   ├── Meshes/
  │   │   └── Refined/      <- Our target folder
  │   │       ├── gus_refined.glb
  │   │       ├── gus_refined.refiner.json   (metadata)
  │   │       └── ...
  │   └── ...
  ├── MyGame.uproject       (Unreal project file)
  └── ...
```

## Implementation Path

1. **Export Helper**: `export_to_glb(mesh, output_path)` in `refiner_core/exporters.py`
2. **Unreal Bridge**: `refiner_core/unreal_bridge.py` to validate project, stage GLBs + metadata
3. **CLI Flags**: `--unreal-project`, `--unreal-assets-folder` to route outputs
4. **Metadata JSON**: Track source file, refinement params, export timestamp
5. **Testing**: End-to-end with mock Unreal project structure

## Alternative: Add Assimp

If GLB is insufficient (e.g., require FBX for skeletal animation), install `assimp`:
```bash
pip install assimp
```
Then wrap CLI: `assimp export input.glb output.fbx`

**Decision**: Start with GLB. Assimp can be added as optional fallback.
