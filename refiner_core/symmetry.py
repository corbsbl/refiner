from typing import Optional, Tuple
import numpy as np
from .utils import eprint


def try_import_trimesh():
    import trimesh
    return trimesh


def _compute_mesh_center_and_extent(mesh) -> Tuple[np.ndarray, np.ndarray]:
    bounds = getattr(mesh, 'bounds', None)
    if bounds is not None:
        center = bounds.mean(axis=0)
        extent = bounds[1] - bounds[0]
        return center, extent
    center = getattr(mesh, 'centroid', np.zeros(3))
    extent = getattr(mesh, 'extents', np.ones(3))
    try:
        extent = np.asarray(extent)
    except Exception:
        extent = np.ones(3)
    return center, extent


def _mirror_vertices(vertices: np.ndarray, axis: str, center: float) -> np.ndarray:
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    mirrored = vertices.copy()
    mirrored[:, idx] = 2 * center - mirrored[:, idx]
    return mirrored


def _pick_axis_by_extent(mesh) -> str:
    _, extent = _compute_mesh_center_and_extent(mesh)
    axis_idx = int(np.argmax(np.abs(extent)))
    return ['x', 'y', 'z'][axis_idx]


def _split_indices_by_axis(mesh, axis: str, center_value: float, eps: float = 1e-6):
    coords = mesh.vertices[:, {'x': 0, 'y': 1, 'z': 2}[axis]]
    neg_idx = np.nonzero(coords <= center_value + eps)[0]
    pos_idx = np.nonzero(coords >= center_value - eps)[0]
    return neg_idx, pos_idx


def _subset_mesh_by_vertex_indices(trimesh_mod, mesh, keep_vertex_indices: np.ndarray):
    mask = np.isin(mesh.faces, keep_vertex_indices)
    face_keep = np.all(mask, axis=1)
    if not np.any(face_keep):
        return None
    sub = mesh.submesh([face_keep], only_watertight=False, append=True, repair=False)
    if isinstance(sub, list):
        if len(sub) == 0:
            return None
        sub = max(sub, key=lambda m: getattr(m, 'area', 0.0))
    return sub


def symmetry_repair_trimesh_inplace(mesh, axis: Optional[str] = None, prefer: str = 'auto', weld: bool = True,
                                    tolerance: float = 1e-5) -> bool:
    trimesh = try_import_trimesh()
    if axis is None:
        axis = _pick_axis_by_extent(mesh)
    center, _ = _compute_mesh_center_and_extent(mesh)
    center_value = center[{'x': 0, 'y': 1, 'z': 2}[axis]]
    neg_idx, pos_idx = _split_indices_by_axis(mesh, axis, center_value)
    neg_mesh = _subset_mesh_by_vertex_indices(trimesh, mesh, neg_idx)
    pos_mesh = _subset_mesh_by_vertex_indices(trimesh, mesh, pos_idx)
    pick = None
    if prefer == 'negative' and neg_mesh is not None:
        pick = ('neg', neg_mesh)
    elif prefer == 'positive' and pos_mesh is not None:
        pick = ('pos', pos_mesh)
    else:
        a_neg = getattr(neg_mesh, 'area', 0.0) if neg_mesh is not None else 0.0
        a_pos = getattr(pos_mesh, 'area', 0.0) if pos_mesh is not None else 0.0
        pick = ('neg', neg_mesh) if a_neg > a_pos else ('pos', pos_mesh)
    if pick[1] is None:
        return False
    _, half = pick
    mirrored_vertices = _mirror_vertices(half.vertices, axis, center_value)
    mirrored = trimesh.Trimesh(vertices=mirrored_vertices, faces=half.faces, process=False)
    combined = trimesh.util.concatenate([half, mirrored])
    if weld:
        try:
            combined.merge_vertices(epsilon=tolerance)
        except Exception:
            pass
    mesh.vertices = combined.vertices
    mesh.faces = combined.faces
    # Refresh caches/normals safely without passing None
    try:
        if hasattr(mesh, 'remove_unreferenced_vertices'):
            mesh.remove_unreferenced_vertices()
    except Exception:
        pass
    try:
        if hasattr(mesh, 'fix_normals'):
            mesh.fix_normals()
        else:
            import numpy as np
            mask = np.ones(len(mesh.vertices), dtype=bool)
            if hasattr(mesh, 'update_vertices'):
                mesh.update_vertices(mask=mask)
    except Exception:
        pass
    return True
