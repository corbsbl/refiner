from pathlib import Path
from typing import List, Optional

try:  # pragma: no cover - optional dependency during linting
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

from .utils import eprint, ensure_dir


def _require_numpy():
    if np is None:  # type: ignore
        raise RuntimeError("NumPy is required for refining operations")
    return np  # type: ignore


def export_same_format(obj, output_path: Path):
    ensure_dir(output_path.parent)
    if hasattr(obj, 'export'):
        obj.export(output_path.as_posix())
        return
    # Lazy import
    from importlib import import_module
    trimesh = import_module('trimesh')
    scene = trimesh.Scene(obj)
    scene.export(output_path.as_posix())


def process_file(path: Path, outdir: Path, method: str, iterations: int, lamb: float, nu: float,
                 smooth_textures: bool, texture_method: str, bilateral_d: int, bilateral_sigma_color: float,
                 bilateral_sigma_space: float, gaussian_ksize: int, gaussian_sigma: float,
                 pre_repair: bool = True,
                 unwrap_uv_with_blender: bool = False,
                 unwrap_attempts: int = 2,
                 uv_min_coverage: float = 50.0,
                 uv_max_overlap_pct: float = 10.0,
                 uv_max_oob_pct: float = 5.0,
                 unwrap_angle_limit: float = 66.0,
                 unwrap_island_margin: float = 0.02,
                 unwrap_pack_margin: float = 0.003,
                 blender_exe: Optional[str] = None) -> Optional[Path]:
    # Lazy imports to avoid heavy deps during CLI --help
    from .loaders import load_scene_or_mesh, try_blender_unwrap_uv
    from .smoothing import smooth_trimesh_inplace
    from .textures import find_exported_mtl, smooth_textures_in_mtl
    ext = path.suffix.lower()
    supported_mesh = {'.obj', '.glb', '.gltf', '.stl'}
    source_path = path

    if ext == '.fbx':
        eprint(f"FBX not processed automatically: {path.name}. Consider converting to GLB/OBJ (e.g., via Blender) and rerun.")
        return None
    if ext not in supported_mesh:
        eprint(f"Skipping unsupported file: {path.name}")
        return None


    # Optional Blender UV unwrap step (works best before smoothing). If enabled,
    # or if no UVs detected after load, iterate up to unwrap_attempts until thresholds pass.
    def _has_uv(m) -> bool:
        try:
            v = getattr(m, 'visual', None)
            return v is not None and getattr(v, 'uv', None) is not None and len(v.uv) > 0
        except Exception:
            return False

    def _uv_metrics(m) -> dict:
        from .analyzer import analyze_loaded
        rep = analyze_loaded(m, is_scene=False)
        mrep = rep['meshes'][0] if rep.get('meshes') else {}
        # Compute coverage/overlap with the rasterizer by reusing uv_analyzer raster if needed
        # For now, rely on presence and OOB, and symmetry metrics for gating; extend later.
        return {
            'has_uv': bool(mrep.get('has_uv', False)),
            'uv_oob_vertex_pct': float(mrep.get('uv_oob_vertex_pct', 0.0) or 0.0),
        }

    unwrap_needed = unwrap_uv_with_blender
    # We'll revisit after load below to auto-enable unwrap if missing UVs
    obj, is_scene = load_scene_or_mesh(source_path)
    if not is_scene and not _has_uv(obj):
        unwrap_needed = True
    # Auto-unwrap loop
    if unwrap_needed:
        for attempt in range(max(1, int(unwrap_attempts))):
            uv_dir = outdir / "_uvwrap"
            ensure_dir(uv_dir)
            uv_path = try_blender_unwrap_uv(
                source_path, uv_dir, blender_exe=blender_exe,
                angle_limit=unwrap_angle_limit,
                island_margin=unwrap_island_margin,
                pack_margin=unwrap_pack_margin,
            )
            if uv_path and uv_path.exists():
                source_path = uv_path
                obj, is_scene = load_scene_or_mesh(source_path)
                if not is_scene:
                    met = _uv_metrics(obj)
                    # Basic acceptance gate; expand to include coverage/overlap when available
                    if met['has_uv'] and met['uv_oob_vertex_pct'] <= uv_max_oob_pct:
                        break
            else:
                break

    try:
        from importlib import import_module
        trimesh = import_module('trimesh')
        Scene = getattr(trimesh, 'Scene')
        Trimesh = getattr(trimesh, 'Trimesh')
        if is_scene and isinstance(obj, Scene) and (len(getattr(obj, 'geometry', {})) == 0):
            eprint(f"Empty scene detected in {path.name}; skipping.")
            return None
    except Exception:
        pass

    # Pre-repair, then smoothing + symmetry (pre-repair enforced by default)
    from .repair import pre_repair_trimesh
    
    def _num_vertices(m) -> int:
        v = getattr(m, 'vertices', None)
        try:
            return int(len(v)) if v is not None else 0
        except Exception:
            try:
                np_mod = _require_numpy()
                return int(np_mod.asarray(v).shape[0])
            except Exception:
                return 0
    if is_scene:
        try:
            geoms = getattr(obj, 'geometry', {})
            count = 0
            for name, geom in geoms.items():
                try:
                    # Defensive normalization to avoid 'len() of unsized object'
                    np_mod = _require_numpy()
                    try:
                        if getattr(geom, 'vertices', None) is not None:
                            geom.vertices = np_mod.ascontiguousarray(np_mod.asarray(geom.vertices, dtype=np.float64))
                        if getattr(geom, 'faces', None) is not None:
                            geom.faces = np_mod.ascontiguousarray(np_mod.asarray(geom.faces, dtype=np.int64))
                    except Exception:
                        pass
                    if pre_repair:
                        pre_repair_trimesh(geom)
                    # Adaptive smoothing parameters based on size
                    nit = max(1, int(iterations))
                    lam = float(lamb)
                    nv = _num_vertices(geom)
                    if nv > 500_000:
                        nit = max(1, iterations // 2)
                        lam = min(lam, 0.4)
                    elif nv < 50_000:
                        nit = iterations
                    smooth_trimesh_inplace(geom, method, nit, lam, nu)
                    # Symmetry repair removed: we now rely on Chamfer-based symmetry
                    # scoring in the analyzer and do not perform automatic symmetry repair here.
                    count += 1
                except Exception as ex:
                    eprint(f"Failed smoothing geometry {name}: {ex}")
            if count == 0:
                eprint("No geometries smoothed in scene; attempting merge-and-smooth fallback.")
                try:
                    from importlib import import_module as _im
                    trimesh = _im('trimesh')
                    meshes = []
                    for gname, g in geoms.items():
                        if isinstance(g, trimesh.Trimesh) and getattr(g, 'faces', None) is not None:
                            try:
                                if len(g.faces) > 0 and len(g.vertices) > 0:
                                    meshes.append(g)
                            except Exception:
                                pass
                    if len(meshes) > 0:
                        merged = trimesh.util.concatenate(meshes)
                        # Normalize arrays before smoothing
                        np_mod = _require_numpy()
                        try:
                            if getattr(merged, 'vertices', None) is not None:
                                merged.vertices = np_mod.ascontiguousarray(np_mod.asarray(merged.vertices, dtype=np.float64))
                            if getattr(merged, 'faces', None) is not None:
                                merged.faces = np_mod.ascontiguousarray(np_mod.asarray(merged.faces, dtype=np.int64))
                        except Exception:
                            pass
                        if pre_repair:
                            pre_repair_trimesh(merged)
                        # Adaptive params for merged mesh
                        nit = max(1, int(iterations))
                        lam = float(lamb)
                        nv = _num_vertices(merged)
                        if nv > 500_000:
                            nit = max(1, iterations // 2)
                            lam = min(lam, 0.4)
                        elif nv < 50_000:
                            nit = iterations
                        smooth_trimesh_inplace(merged, method, nit, lam, nu)
                        # Symmetry repair removed for merged meshes; analyzer will report
                        # Chamfer-based symmetry metrics for human review.
                        obj = merged
                        is_scene = False
                    else:
                        eprint("Merge fallback found no valid triangle meshes; exporting as-is.")
                except Exception as ex2:
                    eprint(f"Merge-and-smooth fallback failed: {ex2}")
        except Exception:
            pass
    else:
        if pre_repair:
            pre_repair_trimesh(obj)
        # Adaptive params for single mesh
        nit = max(1, int(iterations))
        lam = float(lamb)
        nv = _num_vertices(obj)
        if nv > 500_000:
            nit = max(1, iterations // 2)
            lam = min(lam, 0.4)
        elif nv < 50_000:
            nit = iterations
        smooth_trimesh_inplace(obj, method, nit, lam, nu)
        # Symmetry repair removed for single meshes; analyzer will report
        # Chamfer-based symmetry metrics for human review.

    # Export
    suffix = '_refined'
    output_name = source_path.stem + suffix + source_path.suffix
    out_path = outdir / output_name
    export_same_format(obj, out_path)

    # Texture smoothing for OBJ
    if smooth_textures and out_path.suffix.lower() == '.obj':
        mtl_path = find_exported_mtl(out_path)
        if mtl_path and mtl_path.exists():
            tex_out_dir = mtl_path.parent
            changed, _ = smooth_textures_in_mtl(
                mtl_path=mtl_path,
                out_dir=tex_out_dir,
                method=texture_method,
                d=bilateral_d,
                sigmaColor=bilateral_sigma_color,
                sigmaSpace=bilateral_sigma_space,
                gaussian_ksize=gaussian_ksize,
                gaussian_sigma=gaussian_sigma,
            )
            print(f"Texture smoothing: {changed} texture(s) updated for {out_path.name}")
        else:
            eprint(f"No MTL found for OBJ {out_path.name}; skipping texture smoothing.")
    return out_path


def process_path(input_path: Path, outdir: Path, **kwargs) -> List[Path]:
    ensure_dir(outdir)
    results: List[Path] = []
    if input_path.is_dir():
        for ext in ('*.obj', '*.glb', '*.gltf', '*.stl'):
            for p in input_path.rglob(ext):
                res = process_file(p, outdir, **kwargs)
                if res is not None:
                    results.append(res)
    else:
        res = process_file(input_path, outdir, **kwargs)
        if res is not None:
            results.append(res)
    return results
