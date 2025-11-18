from pathlib import Path
import shutil
import subprocess
from typing import Optional, Tuple
import numpy as np


def eprint(*a, **k):
    import sys
    print(*a, file=sys.stderr, **k)


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


def try_import_cv2():
    import cv2
    return cv2


def load_scene_or_mesh(path: Path):
    trimesh, _ = try_import_trimesh()
    loaded = trimesh.load(path.as_posix(), force=None)
    if isinstance(loaded, list):
        loaded = trimesh.util.concatenate(loaded)
    from trimesh import Scene, Trimesh
    if isinstance(loaded, Scene):
        return loaded, True
    if isinstance(loaded, Trimesh):
        return loaded, False
    try:
        scene = trimesh.Scene(loaded)
        return scene, True
    except Exception:
        return loaded, False


def try_blender_convert(input_path: Path, out_dir: Path, blender_exe: Optional[str] = None) -> Optional[Path]:
    exe = blender_exe or shutil.which('blender') or shutil.which('blender.exe')
    if not exe:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out_obj = out_dir / (input_path.stem + "_blender.obj")
    script_path = out_dir / "import_export_obj.py"
    script = f"""
import bpy, sys, os
in_path = r"{input_path.as_posix()}"
out_path = r"{out_obj.as_posix()}"
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(in_path)[1].lower()
try:
    if ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=in_path)
    elif ext in ['.obj']:
        bpy.ops.wm.obj_import(filepath=in_path)
    elif ext in ['.fbx']:
        bpy.ops.import_scene.fbx(filepath=in_path)
    else:
        sys.exit(5)
except Exception as ex:
    print('Blender import failed:', ex)
    sys.exit(6)
for obj in bpy.data.objects:
    obj.select_set(True)
try:
    bpy.ops.wm.obj_export(filepath=out_path, export_materials=False)
except Exception as ex:
    print('Blender OBJ export failed:', ex)
    sys.exit(7)
print('Exported OBJ:', out_path)
"""
    script_path.write_text(script, encoding='utf-8')
    try:
        proc = subprocess.run([exe, "-b", "-noaudio", "--python", str(script_path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(out_dir))
        if proc.returncode == 0 and out_obj.exists():
            return out_obj
        else:
            eprint(proc.stdout)
            eprint(proc.stderr)
            return None
    except Exception as ex:
        eprint(f"Failed to run Blender: {ex}")
        return None


def try_blender_unwrap_uv(
    input_path: Path,
    out_dir: Path,
    blender_exe: Optional[str] = None,
    angle_limit: float = 66.0,
    island_margin: float = 0.02,
    pack_margin: float = 0.003,
) -> Optional[Path]:
    exe = blender_exe or shutil.which('blender') or shutil.which('blender.exe')
    if not exe:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out_obj = out_dir / (input_path.stem + "_uv.obj")
    script_path = out_dir / "unwrap_uv_and_export_obj.py"
    script = f"""
import bpy, sys, os
in_path = r"{input_path.as_posix()}"
out_path = r"{out_obj.as_posix()}"
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(in_path)[1].lower()
try:
    if ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=in_path)
    elif ext in ['.obj']:
        bpy.ops.wm.obj_import(filepath=in_path)
    elif ext in ['.fbx']:
        bpy.ops.import_scene.fbx(filepath=in_path)
    else:
        sys.exit(5)
except Exception as ex:
    print('Blender import failed:', ex)
    sys.exit(6)

for obj in list(bpy.data.objects):
    if obj.type != 'MESH':
        continue
    bpy.context.view_layer.objects.active = obj
    for o in bpy.data.objects:
        o.select_set(False)
    obj.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        # Smart UV project
        bpy.ops.uv.smart_project(angle_limit={angle_limit}, island_margin={island_margin})
        # Pack islands (optional)
        bpy.ops.uv.pack_islands(margin={pack_margin})
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as ex:
        print('UV unwrap failed for object', obj.name, ex)

try:
    bpy.ops.wm.obj_export(filepath=out_path, export_materials=False)
except Exception as ex:
    print('Blender OBJ export failed:', ex)
    sys.exit(7)
print('Exported OBJ with UV:', out_path)
"""
    script_path.write_text(script, encoding='utf-8')
    try:
        proc = subprocess.run([exe, "-b", "-noaudio", "--python", str(script_path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(out_dir))
        if proc.returncode == 0 and out_obj.exists():
            return out_obj
        else:
            eprint(proc.stdout)
            eprint(proc.stderr)
            return None
    except Exception as ex:
        eprint(f"Failed to run Blender: {ex}")
        return None


def try_assimp_convert(input_path: Path, out_dir: Path) -> Optional[Path]:
    exe = shutil.which('assimp') or shutil.which('assimp.exe')
    if not exe:
        return None
    out_obj = out_dir / (input_path.stem + '_assimp.obj')
    try:
        proc = subprocess.run([exe, 'export', str(input_path), str(out_obj)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(out_dir))
        if proc.returncode == 0 and out_obj.exists():
            return out_obj
        else:
            eprint(proc.stdout)
            eprint(proc.stderr)
            return None
    except Exception as ex:
        eprint(f'Failed to run assimp: {ex}')
        return None


def try_open3d_convert(input_path: Path, out_dir: Path) -> Optional[Path]:
    o3d = try_import_open3d()
    if o3d is None:
        return None
    out_obj = out_dir / (input_path.stem + '_o3d.obj')
    try:
        read_triangle_model = getattr(o3d.io, 'read_triangle_model', None)
        model = None
        if read_triangle_model is not None and input_path.suffix.lower() in {'.gltf', '.glb'}:
            model = read_triangle_model(str(input_path))
        if model is not None and hasattr(model, 'meshes') and len(model.meshes) > 0:
            merged = None
            for m in model.meshes:
                merged = m.mesh if merged is None else (merged + m.mesh)
            if merged and len(np.asarray(merged.triangles)) > 0:
                if o3d.io.write_triangle_mesh(str(out_obj), merged, write_triangle_uvs=True):
                    return out_obj
        mesh = o3d.io.read_triangle_mesh(str(input_path))
        if mesh is not None and len(np.asarray(mesh.triangles)) > 0:
            if o3d.io.write_triangle_mesh(str(out_obj), mesh, write_triangle_uvs=True):
                return out_obj
    except Exception as ex:
        eprint(f'Open3D fallback failed: {ex}')
        return None
    return None
