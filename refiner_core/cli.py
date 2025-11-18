import argparse
from pathlib import Path
import sys

from .utils import eprint
from .pipeline import process_path
from .exporters import api_export
from .unreal_bridge import stage_to_unreal, stage_to_deferred


def main(argv=None):
    parser = argparse.ArgumentParser(description='Refine 3D assets: smooth vertices and optionally smooth textures (OBJ).')
    parser.add_argument('input', help='Path to a file (.obj/.glb/.gltf/.fbx) or a directory to process recursively')
    parser.add_argument('-o', '--outdir', default='output', help='Output directory (default: output)')

    # Mesh smoothing parameters
    parser.add_argument('--method', choices=['taubin', 'laplacian'], default='taubin', help='Mesh smoothing method')
    parser.add_argument('--iterations', type=int, default=10, help='Smoothing iterations')
    parser.add_argument('--lambda', dest='lamb', type=float, default=0.5, help='Lambda parameter for smoothing')
    parser.add_argument('--nu', type=float, default=-0.53, help='Nu parameter for Taubin smoothing')

    # Texture smoothing options (OBJ)
    parser.add_argument('--smooth-textures', action='store_true', help='Enable smoothing of OBJ diffuse textures (map_Kd)')
    parser.add_argument('--texture-method', choices=['bilateral', 'gaussian'], default='bilateral', help='Texture smoothing method')
    parser.add_argument('--bilateral-d', type=int, default=9, help='Bilateral filter diameter')
    parser.add_argument('--bilateral-sigma-color', type=float, default=75.0, help='Bilateral filter sigmaColor')
    parser.add_argument('--bilateral-sigma-space', type=float, default=75.0, help='Bilateral filter sigmaSpace')
    parser.add_argument('--gaussian-ksize', type=int, default=5, help='Gaussian kernel size (odd)')
    parser.add_argument('--gaussian-sigma', type=float, default=1.2, help='Gaussian sigma')

    # (Symmetry repair has been removed from the public CLI; analyzer still reports symmetry metrics.)

    # Fallback conversion options
    parser.add_argument('--blender-fallback', action='store_true', help='If GLB/GLTF loads empty, try Blender to convert to OBJ and retry')
    parser.add_argument('--blender-exe', type=str, default=None, help='Path to blender executable if not on PATH')
    parser.add_argument('--assimp-fallback', action='store_true', help='If GLB/GLTF loads empty, try assimp CLI to convert to OBJ and retry')
    parser.add_argument('--open3d-fallback', action='store_true', help='If GLB/GLTF loads empty, try Open3D to convert to OBJ and retry')

    # Inspect only (no write) for debugging GLB/GLTF
    parser.add_argument('--inspect-only', action='store_true', help='Print a quick summary of the input and exit (for debugging)')
    parser.add_argument('--preconvert', action='store_true', help='Before processing GLB/GLTF, convert to OBJ (via Open3D/Assimp/Blender) and process the converted file')
    parser.add_argument('--pre-repair', action='store_true', help='Run mesh pre-repair (deduplicate, remove degenerate, weld) before smoothing (default: on)')
    parser.add_argument('--no-pre-repair', action='store_true', help='Disable pre-repair')
    parser.add_argument('--unwrap-uv-with-blender', action='store_true', help='Use Blender headless to unwrap UVs before refining (requires Blender)')
    parser.add_argument('--unwrap-attempts', type=int, default=2, help='Max unwrap attempts if UVs missing or fail thresholds')
    parser.add_argument('--cxprj-thickness', type=float, default=1.0, help='Extrusion thickness when converting CXPRJ projects to meshes')
    parser.add_argument('--cxprj-scale', type=float, default=1.0, help='Uniform scale factor applied after CXPRJ conversion')
    parser.add_argument('--uv-min-coverage', type=float, default=50.0, help='Minimum UV coverage percent (future use)')
    parser.add_argument('--uv-max-overlap-pct', type=float, default=10.0, help='Maximum UV overlap percent (future use)')
    parser.add_argument('--uv-max-oob-pct', type=float, default=5.0, help='Maximum percent of UV vertices out of [0,1]')
    parser.add_argument('--unwrap-angle-limit', type=float, default=66.0, help='Blender smart project angle limit')
    parser.add_argument('--unwrap-island-margin', type=float, default=0.02, help='Blender smart project island margin')
    parser.add_argument('--unwrap-pack-margin', type=float, default=0.003, help='Blender pack islands margin')
    # aggressive symmetry option removed from CLI

    # API-style outputs
    parser.add_argument('--job-id', type=str, default=None, help='If set, write API-style outputs under outputs/<job_id>/')
    parser.add_argument('--api-formats', nargs='*', choices=['mesh', 'obj', 'ply', 'glb'], default=None,
                        help='API formats to export (mesh/obj/ply/glb). mesh implies OBJ by default')
    
    # Analysis-only
    parser.add_argument('--analyze-only', action='store_true', help='Analyze model(s) and print a summary without refining')
    parser.add_argument('--analysis-json', type=str, default=None, help='Write detailed analysis JSON to this path')
    parser.add_argument('--debug', action='store_true', help='Print exception tracebacks on errors')
    parser.add_argument('--unreal-project', type=str, default=None, help='Path to an Unreal .uproject to stage resulting GLBs into')
    parser.add_argument('--defer-unreal-import', action='store_true', help='Stage outputs into a deferred folder outside Content (prevent auto-import). Use --unreal-project to enable')

    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    if not input_path.exists():
        eprint(f"Input path not found: {input_path}")
        return 1

    if args.inspect_only:
        try:
            if input_path.suffix.lower() in {'.glb', '.gltf'}:
                from importlib import import_module
                pygltflib = import_module('pygltflib')
                glb = pygltflib.GLTF2().load_binary(str(input_path)) if input_path.suffix.lower()=='.glb' else pygltflib.GLTF2().load(str(input_path))
                print('extensionsRequired =', glb.extensionsRequired or [])
                print('extensionsUsed     =', glb.extensionsUsed or [])
                print('nodes    =', len(glb.nodes or []))
                print('meshes   =', len(glb.meshes or []))
                print('materials=', len(glb.materials or []))
        except Exception as ex:
            eprint(f'Inspect failed: {ex}')
        return 0

    if args.analyze_only:
        try:
            from .analyzer import analyze_path
            import json
            from pathlib import Path as P
            reports = []
            if input_path.is_dir():
                for ext in ('*.obj', '*.glb', '*.gltf'):
                    for p in input_path.rglob(ext):
                        rep = analyze_path(p)
                        reports.append(rep)
                        # Print per-file summary
                        print(rep.get('file'))
                        for m in rep.get('meshes', []):
                            name = m.get('name', 'mesh')
                            if not m.get('has_geometry', True):
                                print(f"  {name}: no geometry ({m.get('reason','')})")
                                continue
                            uv_txt = 'no UVs' if not m.get('has_uv', False) else f"UV oob={m.get('uv_oob_vertex_pct', 0):.2f}%"
                            print(f"  {name}: V={m.get('num_vertices')} F={m.get('num_faces')} watertight={m.get('is_watertight')} comps={m.get('num_components')} {uv_txt} sym_best={m.get('symmetry_best_axis')} ({m.get('symmetry_best_median_distance')})")
                payload = {"count": len(reports), "files": reports}
            else:
                rep = analyze_path(input_path)
                reports = [rep]
                # Print summary
                print(rep.get('file'))
                for m in rep.get('meshes', []):
                    name = m.get('name', 'mesh')
                    if not m.get('has_geometry', True):
                        print(f"  {name}: no geometry ({m.get('reason','')})")
                        continue
                    uv_txt = 'no UVs' if not m.get('has_uv', False) else f"UV oob={m.get('uv_oob_vertex_pct', 0):.2f}%"
                    print(f"  {name}: V={m.get('num_vertices')} F={m.get('num_faces')} watertight={m.get('is_watertight')} comps={m.get('num_components')} {uv_txt} sym_best={m.get('symmetry_best_axis')} ({m.get('symmetry_best_median_distance')})")
                payload = rep
            if args.analysis_json:
                p = P(args.analysis_json).expanduser().resolve()
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(payload, indent=2), encoding='utf-8')
                print(f"Analysis JSON written: {p}")
        except Exception as ex:
            eprint(f"Analysis failed: {ex}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 2
        return 0

    try:
        results = process_path(
            input_path=input_path,
            outdir=outdir,
            method=args.method,
            iterations=args.iterations,
            lamb=args.lamb,
            nu=args.nu,
            smooth_textures=args.smooth_textures,
            texture_method=args.texture_method,
            bilateral_d=args.bilateral_d,
            bilateral_sigma_color=args.bilateral_sigma_color,
            bilateral_sigma_space=args.bilateral_sigma_space,
            gaussian_ksize=args.gaussian_ksize,
            gaussian_sigma=args.gaussian_sigma,
            symmetry=False,
            symmetry_axis=None,
            symmetry_prefer='auto',
            symmetry_weld=False,
            symmetry_tolerance=1e-5,
            blender_fallback=args.blender_fallback,
            blender_exe=args.blender_exe,
            assimp_fallback=args.assimp_fallback,
            open3d_fallback=args.open3d_fallback,
            preconvert=args.preconvert,
            pre_repair=(False if args.no_pre_repair else True),
            unwrap_uv_with_blender=args.unwrap_uv_with_blender,
            unwrap_attempts=args.unwrap_attempts,
            uv_min_coverage=args.uv_min_coverage,
            uv_max_overlap_pct=args.uv_max_overlap_pct,
            uv_max_oob_pct=args.uv_max_oob_pct,
            unwrap_angle_limit=args.unwrap_angle_limit,
            unwrap_island_margin=args.unwrap_island_margin,
            unwrap_pack_margin=args.unwrap_pack_margin,
            aggressive_symmetry=False,
            cxprj_thickness=args.cxprj_thickness,
            cxprj_scale=args.cxprj_scale,
        )
    except Exception as ex:
        eprint(f"Processing failed: {ex}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 2

    if results:
        print("Refined files:")
        for p in results:
            print(f" - {p}")
        # Optionally stage GLB outputs into an Unreal project
        if args.unreal_project:
            from pathlib import Path
            uproject = Path(args.unreal_project).expanduser().resolve()
            staged = []
            for p in results:
                ppath = Path(p)
                # Only stage GLB files by default
                if ppath.suffix.lower() != '.glb':
                    continue
                try:
                    if args.defer_unreal_import:
                        dest_glb, dest_meta = stage_to_deferred(ppath, uproject)
                    else:
                        dest_glb, dest_meta = stage_to_unreal(ppath, uproject)
                    staged.append((dest_glb, dest_meta))
                    print(f"Staged to Unreal: {dest_glb}")
                except Exception as ex:
                    eprint(f"Unreal staging failed for {ppath}: {ex}")
        if args.job_id and args.api_formats:
            try:
                api_dir = api_export(args.job_id, results[0], args.api_formats)
                print(f"API outputs written under: {api_dir}")
            except Exception as ex:
                eprint(f"API export failed: {ex}")
        return 0
    else:
        print("No files refined.")
        return 0
