"""Refiner: 3D Mesh Refinement & Unreal Engine Integration Pipeline.

Modern CLI with subcommands for analysis, processing, and Unreal integration.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .utils import eprint
from .config import PipelineConfig
from .pipeline import process_path


def _add_smoothing_args(parser: argparse.ArgumentParser) -> None:
    """Add mesh smoothing arguments to parser."""
    parser.add_argument('--method', choices=['taubin', 'laplacian'], default='taubin',
                        help='Mesh smoothing method (default: taubin)')
    parser.add_argument('--iterations', type=int, default=10,
                        help='Smoothing iterations (default: 10)')
    parser.add_argument('--lambda', dest='lamb', type=float, default=0.5,
                        help='Lambda parameter for smoothing (default: 0.5)')
    parser.add_argument('--nu', type=float, default=-0.53,
                        help='Nu parameter for Taubin smoothing (default: -0.53)')


def _add_texture_args(parser: argparse.ArgumentParser) -> None:
    """Add texture smoothing arguments to parser."""
    parser.add_argument('--smooth-textures', action='store_true',
                        help='Enable smoothing of OBJ diffuse textures (map_Kd)')
    parser.add_argument('--texture-method', choices=['bilateral', 'gaussian'], default='bilateral',
                        help='Texture smoothing method (default: bilateral)')
    parser.add_argument('--bilateral-d', type=int, default=9,
                        help='Bilateral filter diameter (default: 9)')
    parser.add_argument('--bilateral-sigma-color', type=float, default=75.0,
                        help='Bilateral filter sigmaColor (default: 75.0)')
    parser.add_argument('--bilateral-sigma-space', type=float, default=75.0,
                        help='Bilateral filter sigmaSpace (default: 75.0)')
    parser.add_argument('--gaussian-ksize', type=int, default=5,
                        help='Gaussian kernel size, odd (default: 5)')
    parser.add_argument('--gaussian-sigma', type=float, default=1.2,
                        help='Gaussian sigma (default: 1.2)')


def _add_uv_args(parser: argparse.ArgumentParser) -> None:
    """Add UV unwrapping arguments to parser."""
    parser.add_argument('--unwrap-uv-with-blender', action='store_true',
                        help='Use Blender headless to unwrap UVs before refining')
    parser.add_argument('--unwrap-attempts', type=int, default=2,
                        help='Max unwrap attempts if UVs missing/fail (default: 2)')
    parser.add_argument('--uv-min-coverage', type=float, default=50.0,
                        help='Minimum UV coverage percent (default: 50.0)')
    parser.add_argument('--uv-max-overlap-pct', type=float, default=10.0,
                        help='Maximum UV overlap percent (default: 10.0)')
    parser.add_argument('--uv-max-oob-pct', type=float, default=5.0,
                        help='Maximum percent of UV vertices out-of-bounds (default: 5.0)')
    parser.add_argument('--unwrap-angle-limit', type=float, default=66.0,
                        help='Blender smart project angle limit (default: 66.0)')
    parser.add_argument('--unwrap-island-margin', type=float, default=0.02,
                        help='Blender smart project island margin (default: 0.02)')
    parser.add_argument('--unwrap-pack-margin', type=float, default=0.003,
                        help='Blender pack islands margin (default: 0.003)')
    parser.add_argument('--blender-exe', type=str, default=None,
                        help='Path to Blender executable when performing UV unwraps')


def _add_repair_args(parser: argparse.ArgumentParser) -> None:
    """Add mesh repair arguments to parser."""
    parser.add_argument('--pre-repair', action='store_true', dest='pre_repair', default=True,
                        help='Run mesh pre-repair (deduplicate, remove degenerate) [default: enabled]')
    parser.add_argument('--no-pre-repair', action='store_true',
                        help='Disable pre-repair')


def cmd_process(args) -> int:
    """Process (refine) 3D asset(s)."""
    input_path = Path(args.input).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    if not input_path.exists():
        eprint(f"Input path not found: {input_path}")
        return 1

    try:
        config = PipelineConfig.from_args(args)
        results = process_path(
            input_path=input_path,
            outdir=outdir,
            method=config.smoothing.method,
            iterations=config.smoothing.iterations,
            lamb=config.smoothing.lamb,
            nu=config.smoothing.nu,
            smooth_textures=config.texture.smooth_textures,
            texture_method=config.texture.method,
            bilateral_d=config.texture.bilateral_d,
            bilateral_sigma_color=config.texture.bilateral_sigma_color,
            bilateral_sigma_space=config.texture.bilateral_sigma_space,
            gaussian_ksize=config.texture.gaussian_ksize,
            gaussian_sigma=config.texture.gaussian_sigma,
            pre_repair=config.repair.pre_repair,
            unwrap_uv_with_blender=config.uv.unwrap_uv_with_blender,
            unwrap_attempts=config.uv.unwrap_attempts,
            uv_min_coverage=config.uv.min_coverage,
            uv_max_overlap_pct=config.uv.max_overlap_pct,
            uv_max_oob_pct=config.uv.max_oob_pct,
            unwrap_angle_limit=config.uv.angle_limit,
            unwrap_island_margin=config.uv.island_margin,
            unwrap_pack_margin=config.uv.pack_margin,
            blender_exe=getattr(args, 'blender_exe', None),
        )
    except Exception as ex:
        eprint(f"Processing failed: {ex}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 2

    if results:
        print("\nRefined files:")
        for p in results:
            print(f"  {p}")

        return 0
    else:
        print("No files processed.")
        return 0


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
                description='Refiner: Focused 3D Mesh Refinement Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Refine a model with smoothing
    refiner process model.glb -o output --method laplacian --iterations 20

    # Refine a batch from a directory
    refiner process input_dir -o refined_outputs --smooth-textures
        """
    )

    parser.add_argument('--debug', action='store_true', help='Print exception tracebacks')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # PROCESS subcommand
    p_process = subparsers.add_parser('process', help='Refine 3D asset(s)')
    p_process.add_argument('input', help='Path to file or directory')
    p_process.add_argument('-o', '--outdir', default='output', help='Output directory (default: output)')
    _add_smoothing_args(p_process)
    _add_texture_args(p_process)
    _add_uv_args(p_process)
    _add_repair_args(p_process)
    p_process.set_defaults(func=cmd_process)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
