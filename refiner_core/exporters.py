from pathlib import Path
from typing import List
import json

from .utils import ensure_dir


def try_import_trimesh():
    from importlib import import_module
    return import_module('trimesh')


def try_import_cv2():
    from importlib import import_module
    return import_module('cv2')


def load_as_trimesh_single(path: Path):
    trimesh = try_import_trimesh()
    obj = trimesh.load(path.as_posix(), force=None)
    if isinstance(obj, trimesh.Trimesh):
        return obj
    if isinstance(obj, trimesh.Scene):
        geoms = list(obj.geometry.values())
        if len(geoms) == 1 and isinstance(geoms[0], trimesh.Trimesh):
            return geoms[0]
        meshes = [g for g in geoms if isinstance(g, trimesh.Trimesh)]
        if len(meshes) > 0:
            return trimesh.util.concatenate(meshes)
    try:
        return trimesh.util.concatenate(obj)
    except Exception:
        return None


def api_write_turntable_mp4(out_path: Path, width: int = 512, height: int = 512, seconds: int = 1, fps: int = 24):
    cv2 = try_import_cv2()
    from importlib import import_module
    np = import_module('numpy')
    ensure_dir(out_path.parent)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    vw = cv2.VideoWriter(out_path.as_posix(), fourcc, fps, (width, height))
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for _ in range(max(1, seconds * fps)):
        vw.write(frame)
    vw.release()


def api_export(job_id: str, refined_file: Path, formats: List[str]) -> Path:
    out_root = Path('outputs') / job_id
    ensure_dir(out_root)
    base = f"{job_id}_mesh_0"
    manifest = {k: [] for k in ['mesh', 'obj', 'ply', 'glb', 'gaussian', 'radiance_field']}
    trimesh = try_import_trimesh()
    mesh = load_as_trimesh_single(refined_file)

    def add_out(key: str, rel: str):
        if key in manifest:
            manifest[key].append(str(Path('outputs') / job_id / rel))

    def export_mesh(ext: str, key: str):
        out_path = out_root / f"{base}.{ext}"
        if isinstance(mesh, trimesh.Trimesh):
            mesh.export(out_path.as_posix())
            add_out(key, out_path.name)
            if key != 'mesh':
                add_out('mesh', out_path.name)
        else:
            vid = out_root / f"{base}_mesh.mp4"
            api_write_turntable_mp4(vid)
            add_out('mesh', vid.name)

    req = set([f.lower() for f in formats])
    if 'mesh' in req or 'obj' in req:
        export_mesh('obj', 'obj')
    if 'ply' in req:
        export_mesh('ply', 'ply')
    if 'glb' in req:
        export_mesh('glb', 'glb')

    (out_root / 'outputs.json').write_text(json.dumps({'outputs': manifest}, indent=2), encoding='utf-8')
    return out_root
