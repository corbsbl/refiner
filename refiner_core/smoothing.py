import numpy as np
from .utils import eprint


def try_import_trimesh():
    import trimesh
    from trimesh import smoothing as tmsmooth
    return trimesh, tmsmooth


def try_import_open3d():
    try:
        import open3d as o3d
        return o3d
    except Exception:
        return None


def smooth_trimesh_inplace(mesh, method: str, iterations: int, lamb: float, nu: float):
    trimesh, tmsmooth = try_import_trimesh()

    def _safe_len(a) -> int:
        try:
            return int(a.shape[0]) if hasattr(a, 'shape') else len(a)
        except Exception:
            try:
                return int(np.asarray(a).shape[0])
            except Exception:
                return 0

    try:
        if getattr(mesh, 'vertices', None) is not None:
            mesh.vertices = np.ascontiguousarray(np.asarray(mesh.vertices, dtype=np.float64))
        if getattr(mesh, 'faces', None) is not None:
            mesh.faces = np.ascontiguousarray(np.asarray(mesh.faces, dtype=np.int64))
    except Exception:
        pass

    if mesh.vertices is None or _safe_len(mesh.vertices) == 0 or mesh.faces is None or _safe_len(mesh.faces) == 0:
        return

    try:
        if method == 'taubin':
            tmsmooth.filter_taubin(mesh, lamb=lamb, nu=nu, iterations=iterations)
        elif method == 'laplacian':
            tmsmooth.filter_laplacian(mesh, lamb=lamb, iterations=iterations)
        else:
            raise ValueError(f"Unknown method: {method}")
    except Exception as ex:
        o3d = try_import_open3d()
        if o3d is None:
            eprint(f"Trimesh smoothing failed and Open3D not available: {ex}")
            return
        try:
            o3d_mesh = o3d.geometry.TriangleMesh(
                o3d.utility.Vector3dVector(np.asarray(mesh.vertices, dtype=np.float64)),
                o3d.utility.Vector3iVector(np.asarray(mesh.faces, dtype=np.int32))
            )
            if method == 'taubin' and hasattr(o3d_mesh, 'filter_smooth_taubin'):
                o3d_mesh = o3d_mesh.filter_smooth_taubin(number_of_iterations=max(1, int(iterations)))
            elif hasattr(o3d_mesh, 'filter_smooth_laplacian'):
                o3d_mesh = o3d_mesh.filter_smooth_laplacian(number_of_iterations=max(1, int(iterations)))
            else:
                o3d_mesh = o3d_mesh.filter_smooth_simple(number_of_iterations=max(1, int(iterations)))
            if hasattr(o3d_mesh, 'compute_vertex_normals'):
                o3d_mesh.compute_vertex_normals()
            new_vertices = np.asarray(o3d_mesh.vertices)
            if new_vertices is not None and len(new_vertices) == len(mesh.vertices):
                mesh.vertices = new_vertices
                mesh.update_vertices(mask=None)
        except Exception as ex2:
            eprint(f"Open3D smoothing fallback failed: {ex2}")
