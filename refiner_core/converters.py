from __future__ import annotations

import math
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional

from .utils import ensure_dir, eprint


def _load_svg_paths(svg_path: Path) -> List:
    """Extract path data from SVG file using svgpathtools."""
    try:
        from svgpathtools import svg2paths
        from shapely.geometry import Polygon

        paths, _ = svg2paths(svg_path.as_posix())
        polygons = []
        for path in paths:
            try:
                points = []
                for seg in path:
                    points.append((seg.start.real, seg.start.imag))
                # Add the final end point to close the path
                if path and len(path) > 0:
                    last_seg = path[-1]
                    points.append((last_seg.end.real, last_seg.end.imag))
                
                if len(points) >= 3:
                    poly = Polygon(points)
                    if not poly.is_empty and poly.area > 0:
                        polygons.append(poly)
            except Exception:
                pass
        return polygons
    except Exception:
        return []


def convert_cxprj_to_mesh(
    cxprj_path: Path,
    out_dir: Path,
    *,
    thickness: float = 1.0,
    scale: float = 1.0,
    min_polygon_area: float = 1e-3,
    cleanup_extract: bool = True,
) -> Path:
    """Convert a Cricut Design Space project (.cxprj) into a mesh.

    The CXPRJ archive typically bundles SVG assets describing cut paths.
    We extract all SVGs, convert vector paths into polygons using trimesh's
    SVG path loader, extrude each polygon into a thin solid sheet, then merge
    the results into a single mesh suitable for the refiner pipeline.

    Parameters
    ----------
    cxprj_path : Path
        Input CXPRJ archive path.
    out_dir : Path
        Directory where the converted mesh and temporary extracts will reside.
    thickness : float, optional
        Extrusion thickness along +Z (same units as SVG). Defaults to 1.0.
    scale : float, optional
        Uniform scale factor applied to the resulting mesh. Defaults to 1.0.
    min_polygon_area : float, optional
        Polygons with area below this threshold are skipped as artifacts.
    cleanup_extract : bool, optional
        If True, remove the temporary extraction directory on success.

    Returns
    -------
    Path
        Path to the exported mesh file (OBJ).
    """

    if thickness <= 0:
        raise ValueError("thickness must be positive")
    ensure_dir(out_dir)

    extract_dir = out_dir / f"{cxprj_path.stem}_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    ensure_dir(extract_dir)

    try:
        with zipfile.ZipFile(cxprj_path, 'r') as archive:
            archive.extractall(extract_dir)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"CXPRJ appears to be corrupted: {exc}") from exc

    svg_files = sorted(extract_dir.rglob('*.svg'))
    if not svg_files:
        raise RuntimeError("No SVG assets found in CXPRJ archive")

    meshes = []
    warnings: List[str] = []

    from importlib import import_module
    trimesh = import_module('trimesh')

    for svg_path in svg_files:
        try:
            polygons = _load_svg_paths(svg_path)
            eprint(f"[debug] Loaded {len(polygons)} polygons from {svg_path.name}")
            if not polygons:
                warnings.append(f"No polygon data extracted from {svg_path.name}")
                continue

            for poly in polygons:
                try:
                    area = getattr(poly, 'area', 0.0)
                    if not math.isfinite(area) or area < min_polygon_area:
                        eprint(f"[debug] Skipping polygon with area={area} (threshold={min_polygon_area})")
                        continue

                    mesh = trimesh.creation.extrude_polygon(poly, thickness)
                    if scale != 1.0:
                        mesh.apply_scale(scale)
                    mesh.metadata = mesh.metadata or {}
                    mesh.metadata['source_svg'] = svg_path.name
                    meshes.append(mesh)
                    eprint(f"[debug] Extruded polygon: V={len(mesh.vertices)} F={len(mesh.faces)}")
                except Exception as exc:
                    warnings.append(f"Failed to extrude polygon in {svg_path.name}: {exc}")
                    eprint(f"[debug] Extrude failed: {exc}")
                    continue

        except Exception as exc:
            warnings.append(f"Failed to load {svg_path.name}: {exc}")
            eprint(f"[debug] Load failed: {exc}")
            continue

    if not meshes:
        raise RuntimeError("CXPRJ conversion produced no mesh geometry; check SVG contents")

    if len(meshes) == 1:
        combined = meshes[0]
    else:
        combined = trimesh.util.concatenate(meshes)

    output_path = out_dir / f"{cxprj_path.stem}_converted.obj"
    combined.export(output_path.as_posix())

    if warnings:
        for msg in warnings:
            eprint(f"[cxprj] {msg}")

    if cleanup_extract:
        try:
            shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass

    return output_path


__all__ = [
    'convert_cxprj_to_mesh',
]
