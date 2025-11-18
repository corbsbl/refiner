"""Comprehensive mesh analysis module.

Provides detailed geometric, topological, and UV analysis of 3D meshes.
Key features:
- Watertight and winding consistency detection
- Symmetry probing using Chamfer distance metric
- UV validation and out-of-bounds calculation
- Component and degenerate face detection
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


def _imp_trimesh():
    """Lazy import trimesh library."""
    from importlib import import_module
    return import_module('trimesh')


def _imp_numpy():
    """Lazy import numpy library."""
    from importlib import import_module
    return import_module('numpy')


def _analyze_geometry(mesh) -> Dict[str, Any]:
    """Analyze geometric properties of a mesh.
    
    Args:
        mesh: A trimesh.Trimesh object.
        
    Returns:
        Dictionary with keys: has_geometry, num_vertices, num_faces, is_watertight,
        is_winding_consistent, euler_number, num_open_edges, num_degenerate_faces,
        nonfinite_vertex_values, bbox_min, bbox_max, bbox_extents, centroid, num_components.
    """
    np = _imp_numpy()
    tm = _imp_trimesh()
    out: Dict[str, Any] = {}
    v = getattr(mesh, 'vertices', None)
    f = getattr(mesh, 'faces', None)
    verts = np.asarray(v) if v is not None else None
    faces = np.asarray(f) if f is not None else None
    out['has_geometry'] = bool(verts is not None and faces is not None and len(verts) > 0 and len(faces) > 0)
    if not out['has_geometry']:
        out['reason'] = 'no vertices or faces'
        return out
    out['num_vertices'] = int(len(verts))
    out['num_faces'] = int(len(faces))
    # Basic quality flags
    try:
        out['is_watertight'] = bool(getattr(mesh, 'is_watertight', False))
    except Exception:
        out['is_watertight'] = False
    try:
        out['is_winding_consistent'] = bool(getattr(mesh, 'is_winding_consistent', False))
    except Exception:
        out['is_winding_consistent'] = False
    try:
        out['euler_number'] = float(getattr(mesh, 'euler_number', 0.0))
    except Exception:
        out['euler_number'] = 0.0
    # Open edges / boundary
    try:
        out['num_open_edges'] = int(len(mesh.edges_boundary))
    except Exception:
        out['num_open_edges'] = None
    # Degenerate faces
    try:
        out['num_degenerate_faces'] = int(len(mesh.faces_sparse)) - int(len(faces)) if hasattr(mesh, 'faces_sparse') else None
    except Exception:
        out['num_degenerate_faces'] = None
    # Non-finite vertices
    try:
        nonfinite = np.count_nonzero(~np.isfinite(verts))
        out['nonfinite_vertex_values'] = int(nonfinite)
    except Exception:
        out['nonfinite_vertex_values'] = None
    # Bounding box metrics
    try:
        b = mesh.bounds
        out['bbox_min'] = [float(x) for x in b[0]]
        out['bbox_max'] = [float(x) for x in b[1]]
        out['bbox_extents'] = [float(x) for x in (b[1] - b[0])]
    except Exception:
        out['bbox_min'] = out['bbox_max'] = out['bbox_extents'] = None
    try:
        c = mesh.centroid
        out['centroid'] = [float(x) for x in c]
    except Exception:
        out['centroid'] = None
    # Components
    try:
        comps = mesh.split(only_watertight=False)
        out['num_components'] = int(len(comps))
    except Exception:
        out['num_components'] = None
    return out


def _analyze_uv(mesh) -> Dict[str, Any]:
    np = _imp_numpy()
    out: Dict[str, Any] = {}
    uv = None
    try:
        if getattr(mesh, 'visual', None) is not None:
            uv = np.asarray(mesh.visual.uv) if mesh.visual.uv is not None else None
    except Exception:
        uv = None
    if uv is None or uv.size == 0:
        out['has_uv'] = False
        out['reason'] = 'no uv'
        return out
    out['has_uv'] = True
    uv = uv[:, :2].astype(np.float64, copy=False)
    # OOB fraction
    try:
        oob_mask = (uv[:, 0] < 0) | (uv[:, 0] > 1) | (uv[:, 1] < 0) | (uv[:, 1] > 1)
        out['uv_oob_vertex_pct'] = float(np.count_nonzero(oob_mask)) / max(float(len(uv)), 1.0) * 100.0
    except Exception:
        out['uv_oob_vertex_pct'] = None
    return out


def _symmetry_probe(mesh) -> Dict[str, Any]:
    # Replace the older symmetry median-distance probe with a Chamfer-distance based
    # symmetry score. For each axis (x,y,z) we mirror vertices across the axis and
    # compute a symmetric Chamfer distance (mean nearest-neighbor both directions).
    np = _imp_numpy()
    out: Dict[str, Any] = {}
    v = getattr(mesh, 'vertices', None)
    if v is None:
        return out
    V = np.asarray(v, dtype=np.float64)
    if V.size == 0:
        return out
    try:
        b = mesh.bounds
        center = b.mean(axis=0)
    except Exception:
        center = V.mean(axis=0)
    scores = {}
    for axis, idx in {'x': 0, 'y': 1, 'z': 2}.items():
        mirrored = V.copy()
        mirrored[:, idx] = 2 * center[idx] - mirrored[:, idx]
        try:
            # Sample for performance on large meshes
            step = max(1, len(V) // 2048)
            A = V[::step]
            B = mirrored[::step]
            # pairwise distances (A->B)
            d_ab = np.min(np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2), axis=1)
            d_ba = np.min(np.linalg.norm(B[:, None, :] - A[None, :, :], axis=2), axis=1)
            # symmetric Chamfer distance (mean of both directions)
            chamfer = float((d_ab.mean() + d_ba.mean()) / 2.0)
            scores[axis] = chamfer
        except Exception:
            scores[axis] = None
    out['symmetry_median_distance'] = scores
    # pick best axis (smallest Chamfer)
    best_axis = None
    best_val = None
    for a, v in scores.items():
        if v is None:
            continue
        if best_val is None or v < best_val:
            best_val = v
            best_axis = a
    out['symmetry_best_axis'] = best_axis
    out['symmetry_best_median_distance'] = best_val
    # Also expose explicit chamfer value for clarity
    out['symmetry_best_chamfer'] = best_val
    return out


def analyze_loaded(obj, is_scene: bool) -> Dict[str, Any]:
    tm = _imp_trimesh()
    rep: Dict[str, Any] = {'is_scene': bool(is_scene), 'meshes': []}
    if is_scene and isinstance(obj, tm.Scene):
        geoms = getattr(obj, 'geometry', {}) or {}
        for name, g in geoms.items():
            mrep: Dict[str, Any] = {'name': name or 'mesh'}
            mrep.update(_analyze_geometry(g))
            mrep.update(_analyze_uv(g))
            mrep.update(_symmetry_probe(g))
            rep['meshes'].append(mrep)
    else:
        mrep: Dict[str, Any] = {'name': 'mesh'}
        mrep.update(_analyze_geometry(obj))
        mrep.update(_analyze_uv(obj))
        mrep.update(_symmetry_probe(obj))
        rep['meshes'].append(mrep)
    return rep


def analyze_path(path: Path) -> Dict[str, Any]:
    from .loaders import load_scene_or_mesh
    path = Path(path)
    load_path = path
    
    # Convert CXPRJ to mesh if needed
    if path.suffix.lower() == '.cxprj':
        from .converters import convert_cxprj_to_mesh
        from .utils import ensure_dir
        
        temp_convert_dir = Path('output') / '_analyze_convert'
        ensure_dir(temp_convert_dir)
        try:
            # Don't cleanup during analysis (file may be locked)
            load_path = convert_cxprj_to_mesh(path, temp_convert_dir, cleanup_extract=False)
        except Exception as exc:
            from .utils import eprint
            eprint(f"CXPRJ conversion failed: {exc}")
            raise
    
    obj, is_scene = load_scene_or_mesh(load_path)
    rep = analyze_loaded(obj, is_scene)
    rep['file'] = str(path)
    return rep
