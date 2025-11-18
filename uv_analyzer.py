import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np


def eprint(*a, **k):
    import sys
    print(*a, file=sys.stderr, **k)


def try_imports():
    import importlib
    trimesh = importlib.import_module('trimesh')
    cv2 = importlib.import_module('cv2')
    return trimesh, cv2


def load_geometries(path: Path):
    trimesh, _ = try_imports()
    loaded = trimesh.load(path.as_posix(), force=None)
    from trimesh import Scene, Trimesh
    geoms: List[Tuple[str, Any]] = []
    if isinstance(loaded, Scene):
        for name, geom in (loaded.geometry or {}).items():
            geoms.append((name or 'mesh', geom))
    elif isinstance(loaded, Trimesh):
        geoms.append(('mesh', loaded))
    else:
        try:
            scene = trimesh.Scene(loaded)
            for name, geom in (scene.geometry or {}).items():
                geoms.append((name or 'mesh', geom))
        except Exception:
            pass
    return geoms


def wrap01(uv: np.ndarray) -> np.ndarray:
    return np.mod(uv, 1.0)


def tri_areas_2d(uv: np.ndarray, faces: np.ndarray) -> np.ndarray:
    # uv: (N,2), faces: (M,3)
    a = uv[faces[:, 0]]
    b = uv[faces[:, 1]]
    c = uv[faces[:, 2]]
    # area = 0.5 * |(b-a) x (c-a)| in 2D
    v1 = b - a
    v2 = c - a
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    return 0.5 * np.abs(cross)


def tri_areas_3d(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    a = verts[faces[:, 0]]
    b = verts[faces[:, 1]]
    c = verts[faces[:, 2]]
    v1 = b - a
    v2 = c - a
    cross = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(cross, axis=1)


def inverted_uv_tris(uv: np.ndarray, faces: np.ndarray) -> np.ndarray:
    a = uv[faces[:, 0]]
    b = uv[faces[:, 1]]
    c = uv[faces[:, 2]]
    v1 = b - a
    v2 = c - a
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    return cross < 0.0


def rasterize_uv(faces: np.ndarray, uv: np.ndarray, res: int) -> Tuple[np.ndarray, float, float]:
    """Rasterize UV triangles into an accumulation buffer.

    Returns: (accum array, coverage_px, overlap_px)
    """
    _, cv2 = try_imports()
    acc = np.zeros((res, res), dtype=np.uint16)
    # Scale uv to pixel coordinates [0, res-1]
    uv_px = np.clip((uv * (res - 1)).astype(np.float32), 0, res - 1)
    for tri in faces:
        pts = uv_px[tri].astype(np.int32)
        # Build a temp mask
        mask = np.zeros((res, res), dtype=np.uint8)
        # y is v-coordinate mapping to row (flip v to image row if desired)
        cv2.fillConvexPoly(mask, pts[:, [0, 1]], 1)  # pts: [u,v]
        acc += mask.astype(np.uint16)
    coverage_px = int(np.count_nonzero(acc >= 1))
    overlap_px = int(np.count_nonzero(acc >= 2))
    return acc, float(coverage_px), float(overlap_px)


def analyze_geom(name: str, mesh, res: int, wrap_uv: bool) -> Dict[str, Any]:
    result: Dict[str, Any] = {"name": name}
    verts = np.asarray(mesh.vertices) if getattr(mesh, 'vertices', None) is not None else None
    faces = np.asarray(mesh.faces) if getattr(mesh, 'faces', None) is not None else None
    uv = None
    if getattr(mesh, 'visual', None) is not None:
        try:
            uv = np.asarray(mesh.visual.uv) if mesh.visual.uv is not None else None
        except Exception:
            uv = None

    if verts is None or faces is None or verts.size == 0 or faces.size == 0:
        result.update({"has_geometry": False, "reason": "no vertices or faces"})
        return result

    result["has_geometry"] = True
    if uv is None or uv.size == 0:
        result.update({"has_uv": False, "reason": "no uv"})
        return result

    result["has_uv"] = True
    uv = uv[:, :2].astype(np.float64, copy=False)
    faces = faces.astype(np.int64, copy=False)

    # OOB before wrapping
    oob_mask = (uv[:, 0] < 0) | (uv[:, 0] > 1) | (uv[:, 1] < 0) | (uv[:, 1] > 1)
    oob_pct = float(np.count_nonzero(oob_mask)) / float(len(uv)) * 100.0
    result["uv_oob_vertex_pct"] = round(oob_pct, 4)

    uv_wrapped = wrap01(uv) if wrap_uv else uv.copy()

    # Areas and stretching
    uv_area = tri_areas_2d(uv_wrapped, faces)
    geo_area = tri_areas_3d(verts.astype(np.float64), faces)
    valid = geo_area > 1e-12
    stretch = np.zeros_like(geo_area)
    stretch[valid] = uv_area[valid] / geo_area[valid]
    # Use robust stats
    if np.any(valid):
        result["stretch_ratio_mean"] = float(np.mean(stretch[valid]))
        result["stretch_ratio_median"] = float(np.median(stretch[valid]))
    else:
        result["stretch_ratio_mean"] = 0.0
        result["stretch_ratio_median"] = 0.0

    # Inverted UV triangles
    inv_mask = inverted_uv_tris(uv_wrapped, faces)
    result["inverted_tri_pct"] = round(float(np.count_nonzero(inv_mask)) / float(len(faces)) * 100.0, 4)

    # Rasterization into [0,1] to estimate coverage and overlap
    _, coverage_px, overlap_px = rasterize_uv(faces, uv_wrapped, res)
    total_px = float(res * res)
    result["coverage_pct"] = round(coverage_px / total_px * 100.0, 4)
    result["overlap_px"] = int(overlap_px)
    result["overlap_pct_of_covered"] = round((overlap_px / max(coverage_px, 1.0)) * 100.0, 4)

    return result


def analyze_file(path: Path, res: int, wrap_uv: bool) -> Dict[str, Any]:
    geoms = load_geometries(path)
    out: Dict[str, Any] = {
        "file": str(path),
        "geometry_count": len(geoms),
        "meshes": [],
    }
    if len(geoms) == 0:
        out["note"] = "no geometries detected"
        return out
    for name, geom in geoms:
        try:
            out["meshes"].append(analyze_geom(name, geom, res, wrap_uv))
        except Exception as ex:
            out["meshes"].append({"name": name, "error": str(ex)})
    return out


def process_path(input_path: Path, res: int, wrap_uv: bool) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if input_path.is_dir():
        for ext in ('*.obj', '*.glb', '*.gltf'):
            for p in input_path.rglob(ext):
                results.append(analyze_file(p, res, wrap_uv))
    else:
        results.append(analyze_file(input_path, res, wrap_uv))
    return results


def print_summary(reports: List[Dict[str, Any]]):
    for rep in reports:
        print(rep.get("file"))
        meshes = rep.get("meshes", [])
        if len(meshes) == 0:
            print("  (no meshes)")
            continue
        for m in meshes:
            name = m.get("name", "mesh")
            if m.get("error"):
                print(f"  {name}: ERROR {m['error']}")
                continue
            if not m.get("has_geometry", True):
                print(f"  {name}: no geometry ({m.get('reason','')})")
                continue
            if not m.get("has_uv", False):
                print(f"  {name}: no UVs")
                continue
            print(f"  {name}: coverage={m['coverage_pct']}% overlapCovered={m['overlap_pct_of_covered']}% oobVerts={m['uv_oob_vertex_pct']}% invTris={m['inverted_tri_pct']}% stretch(med)={m['stretch_ratio_median']:.6f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description='Analyze UV mapping quality for OBJ/GLB/GLTF meshes')
    ap.add_argument('input', help='File or directory')
    ap.add_argument('--resolution', type=int, default=1024, help='Raster resolution for coverage/overlap')
    ap.add_argument('--no-wrap', action='store_true', help='Do not wrap UVs into [0,1] for coverage calc')
    ap.add_argument('--json-out', type=str, default=None, help='Write full JSON report to this path')
    args = ap.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        eprint(f"Input not found: {input_path}")
        return 1
    try:
        reports = process_path(input_path, args.resolution, not args.no_wrap)
    except Exception as ex:
        eprint(f"Analysis failed: {ex}")
        return 2

    print_summary(reports)
    if args.json_out:
        import json
        outp = Path(args.json_out).expanduser().resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(reports, indent=2), encoding='utf-8')
        print(f"Report written: {outp}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
