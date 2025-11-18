from __future__ import annotations

def _imp_numpy():
    from importlib import import_module
    return import_module('numpy')


def pre_repair_trimesh(mesh, weld_tolerance: float = 1e-5):
    np = _imp_numpy()
    # Ensure arrays are contiguous and proper dtypes
    try:
        if getattr(mesh, 'vertices', None) is not None:
            mesh.vertices = np.ascontiguousarray(np.asarray(mesh.vertices, dtype=np.float64))
        if getattr(mesh, 'faces', None) is not None:
            mesh.faces = np.ascontiguousarray(np.asarray(mesh.faces, dtype=np.int64))
    except Exception:
        pass
    # Remove degenerate/duplicate and unreferenced
    try:
        if hasattr(mesh, 'remove_degenerate_faces'):
            mesh.remove_degenerate_faces()
    except Exception:
        pass
    try:
        if hasattr(mesh, 'remove_duplicate_faces'):
            mesh.remove_duplicate_faces()
    except Exception:
        pass
    try:
        if hasattr(mesh, 'remove_unreferenced_vertices'):
            mesh.remove_unreferenced_vertices()
    except Exception:
        pass
    # Weld close vertices
    try:
        if hasattr(mesh, 'merge_vertices'):
            mesh.merge_vertices(epsilon=weld_tolerance)
    except Exception:
        pass
    # Recompute normals if available
    try:
        if hasattr(mesh, 'fix_normals'):
            mesh.fix_normals()
    except Exception:
        pass
    return mesh
