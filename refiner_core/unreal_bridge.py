from pathlib import Path
import json
import shutil
import os
import time
from typing import Tuple

from .utils import eprint, ensure_dir


def validate_unreal_project(project_path: Path) -> bool:
    """Validate that the given path points to an Unreal .uproject and a Content/ folder.

    Returns True if minimal requirements are present and writable.
    """
    project_path = Path(project_path)
    if not project_path.exists() or project_path.suffix.lower() != '.uproject':
        eprint(f"Not a valid .uproject file: {project_path}")
        return False
    content_dir = project_path.parent / 'Content'
    if not content_dir.exists():
        eprint(f"Content folder missing for Unreal project: {content_dir}")
        return False
    # Check writability by attempting to stat the directory and check permissions
    try:
        test_file = content_dir / '.refiner_write_test'
        test_file.write_text('test', encoding='utf-8')
        test_file.unlink()
    except Exception as ex:
        eprint(f"Content folder not writable: {content_dir} ({ex})")
        return False
    return True


def _write_metadata(glb_path: Path, metadata: dict) -> Path:
    metadata_path = glb_path.with_suffix(glb_path.suffix + '.json')
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata_path


def stage_to_unreal(glb_path: Path, project_path: Path, assets_folder: str = 'Meshes/Refined') -> Tuple[Path, Path]:
    """Stage a GLB asset and a metadata JSON into an Unreal project's Content folder.

    Behavior:
    - Validates `project_path` (.uproject) and Content/ folder.
    - Copies `glb_path` into <uproject_parent>/Content/<assets_folder>/
    - Writes metadata JSON alongside the GLB with fields: source, staged_at, imported=False
    - Sets the filesystem mtime of the copied files to the current time so they appear "newer" to Unreal.

    Returns (glb_dest_path, metadata_dest_path)
    """
    glb_path = Path(glb_path)
    project_path = Path(project_path)

    if not glb_path.exists():
        raise FileNotFoundError(f"GLB source not found: {glb_path}")

    if not validate_unreal_project(project_path):
        raise RuntimeError(f"Unreal project validation failed for: {project_path}")

    target_dir = project_path.parent / 'Content' / Path(assets_folder)
    ensure_dir(target_dir)

    dest_glb = target_dir / glb_path.name
    # Copy GLB (overwrite if exists)
    shutil.copy2(str(glb_path), str(dest_glb))

    # Metadata
    metadata = {
        'source': str(glb_path.resolve()),
        'staged_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'imported': False,
    }
    dest_meta = dest_glb.with_suffix(dest_glb.suffix + '.json')
    dest_meta.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    # Ensure mtimes are current (set both files to now)
    now = time.time()
    try:
        os.utime(dest_glb, (now, now))
        os.utime(dest_meta, (now, now))
    except Exception:
        # Non-fatal; metadata still written
        pass

    return dest_glb, dest_meta


def stage_to_deferred(glb_path: Path, project_path: Path, assets_folder: str = 'Meshes/Refined', deferred_folder: str = 'RefinerDeferred') -> Tuple[Path, Path]:
    """Stage a GLB asset into a deferred staging folder (outside Content).

    This prevents automatic Unreal import until a finalization step moves the asset into the project's Content folder.

    Returns (deferred_glb_path, deferred_meta_path)
    """
    glb_path = Path(glb_path)
    project_path = Path(project_path)

    if not glb_path.exists():
        raise FileNotFoundError(f"GLB source not found: {glb_path}")

    # Create deferred folder at project root: <uproject_parent>/RefinerDeferred/<assets_folder>/
    deferred_dir = project_path.parent / deferred_folder / Path(assets_folder)
    ensure_dir(deferred_dir)

    dest_glb = deferred_dir / glb_path.name
    shutil.copy2(str(glb_path), str(dest_glb))

    metadata = {
        'source': str(glb_path.resolve()),
        'staged_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'imported': False,
        'deferred': True,
    }
    dest_meta = _write_metadata(dest_glb, metadata)

    return dest_glb, dest_meta


def finalize_deferred(deferred_glb_path: Path, project_path: Path, assets_folder: str = 'Meshes/Refined', deferred_folder: str = 'RefinerDeferred') -> Tuple[Path, Path]:
    """Move a deferred GLB (from the RefinerDeferred area) into the project's Content folder and set mtimes.

    deferred_glb_path may be either an absolute path to the deferred GLB or the filename; project_path is the .uproject file.
    Returns (final_glb_path, final_meta_path)
    """
    deferred_glb_path = Path(deferred_glb_path)
    project_path = Path(project_path)

    if not deferred_glb_path.exists():
        raise FileNotFoundError(f"Deferred GLB not found: {deferred_glb_path}")

    # Ensure project is valid (Content folder exists)
    if not project_path.exists() or project_path.suffix.lower() != '.uproject':
        raise RuntimeError(f"Invalid .uproject file: {project_path}")

    content_target = project_path.parent / 'Content' / Path(assets_folder)
    ensure_dir(content_target)

    final_glb = content_target / deferred_glb_path.name

    # If deferred_glb_path is inside the deferred folder, move it; otherwise copy
    try:
        # Prefer atomic move when possible
        shutil.move(str(deferred_glb_path), str(final_glb))
    except Exception:
        shutil.copy2(str(deferred_glb_path), str(final_glb))

    # Update / rewrite metadata: copy existing metadata if present, update fields, set mtime
    deferred_meta = deferred_glb_path.with_suffix(deferred_glb_path.suffix + '.json')
    final_meta = final_glb.with_suffix(final_glb.suffix + '.json')
    metadata = {}
    if deferred_meta.exists():
        try:
            metadata = json.loads(deferred_meta.read_text(encoding='utf-8'))
        except Exception:
            metadata = {}
    metadata.update({'finalized_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'deferred': False, 'imported': False})
    final_meta.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    now = time.time()
    try:
        os.utime(final_glb, (now, now))
        os.utime(final_meta, (now, now))
    except Exception:
        pass

    return final_glb, final_meta
