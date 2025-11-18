from pathlib import Path
from typing import List, Optional, Tuple
import os

from .utils import eprint, ensure_dir


def try_import_cv2():
    import cv2
    return cv2


def parse_obj_for_mtl(obj_path: Path) -> Optional[str]:
    try:
        with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.lower().startswith('mtllib'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1]
    except Exception:
        return None
    return None


def find_exported_mtl(output_obj: Path) -> Optional[Path]:
    mtl_name = parse_obj_for_mtl(output_obj)
    if mtl_name:
        mtl_path = (output_obj.parent / mtl_name).resolve()
        if mtl_path.exists():
            return mtl_path
    guessed = output_obj.with_suffix('.mtl')
    return guessed if guessed.exists() else None


def _extract_texture_path_from_map_kd(tokens: List[str]) -> Optional[str]:
    if len(tokens) < 2:
        return None
    return tokens[-1]


def _rebuild_map_kd_line(prefix: str, tokens: List[str], new_path: str) -> str:
    new_tokens = tokens[:-1] + [new_path]
    return prefix + ' ' + ' '.join(new_tokens) + '\n'


def smooth_textures_in_mtl(mtl_path: Path, out_dir: Path, method: str = 'bilateral', d: int = 9,
                            sigmaColor: float = 75.0, sigmaSpace: float = 75.0,
                            gaussian_ksize: int = 5, gaussian_sigma: float = 1.2) -> Tuple[int, List[Path]]:
    cv2 = try_import_cv2()
    ensure_dir(out_dir)

    try:
        with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as ex:
        eprint(f"Failed to read MTL {mtl_path}: {ex}")
        return 0, []

    changed = 0
    written: List[Path] = []
    new_lines: List[str] = []
    for line in lines:
        if line.lower().startswith('map_kd'):
            prefix = line.strip().split()[0]
            tokens = line.strip().split()[1:]
            tex_rel = _extract_texture_path_from_map_kd(tokens)
            if tex_rel:
                tex_path = (mtl_path.parent / tex_rel).resolve()
                if tex_path.exists():
                    img = cv2.imread(tex_path.as_posix(), cv2.IMREAD_UNCHANGED)
                    if img is None:
                        eprint(f"Warning: couldn't read texture {tex_path}")
                        new_lines.append(line)
                        continue
                    if method == 'bilateral':
                        smoothed = cv2.bilateralFilter(img, d=d, sigmaColor=sigmaColor, sigmaSpace=sigmaSpace)
                    elif method == 'gaussian':
                        k = max(3, int(gaussian_ksize) // 2 * 2 + 1)
                        smoothed = cv2.GaussianBlur(img, (k, k), gaussian_sigma)
                    else:
                        smoothed = img

                    out_name = tex_path.stem + '_smoothed' + tex_path.suffix
                    out_tex_path = (out_dir / out_name).resolve()
                    ensure_dir(out_tex_path.parent)
                    ok = cv2.imwrite(out_tex_path.as_posix(), smoothed)
                    if ok:
                        changed += 1
                        written.append(out_tex_path)
                        new_rel = os.path.relpath(out_tex_path, mtl_path.parent)
                        new_line = _rebuild_map_kd_line(prefix, tokens, new_rel)
                        new_lines.append(new_line)
                    else:
                        eprint(f"Failed to write smoothed texture to {out_tex_path}")
                        new_lines.append(line)
                else:
                    eprint(f"Warning: texture not found {tex_path}")
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if changed > 0:
        try:
            with open(mtl_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as ex:
            eprint(f"Failed to write updated MTL {mtl_path}: {ex}")

    return changed, written
