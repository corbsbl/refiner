"""Capstone-specific CLI commands for Refiner.

Extends the main CLI with capstone workflow integration.
"""

import argparse
from pathlib import Path
from typing import Optional

from .utils import eprint
from .wsl_adapter import RefinerCapstoneIntegration, WSLPathConverter
from .cli_v2 import main as cli_main


def cmd_capstone_status(args) -> int:
    """Show capstone integration status."""
    capstone_root = getattr(args, 'capstone_root', None)
    integration = RefinerCapstoneIntegration(capstone_root)
    
    print(integration.log_integration_status())
    return 0


def cmd_capstone_process_inputs(args) -> int:
    """Process all 3D assets from capstone input directory."""
    import tempfile
    import shutil
    import subprocess
    
    capstone_root = getattr(args, 'capstone_root', None)
    integration = RefinerCapstoneIntegration(capstone_root)

    is_valid, msg = integration.validate()
    if not is_valid:
        eprint(f"Validation failed: {msg}")
        return 1

    input_files = integration.get_capstone_input_files()
    if not input_files:
        print("No input files found in capstone input directory")
        return 0

    output_subdir = getattr(args, 'output_subdir', 'refined_meshes')
    output_dir = integration.get_capstone_output_dir(output_subdir)

    print(f"Processing {len(input_files)} files from capstone input directory")
    print(f"Output directory: {output_dir}")

    # Use Refiner's core process pipeline for each file
    from .pipeline import process_path
    from .config import PipelineConfig

    config = PipelineConfig.from_args(args)
    processed = []
    failed = []
    
    # Create temp directory for processing if needed (UNC paths)
    temp_dir = None
    input_is_unc = any(str(f).startswith(r"\\wsl.localhost") for f in input_files)
    output_is_unc = str(output_dir).startswith(r"\\wsl.localhost")
    
    if input_is_unc:
        temp_dir = Path(tempfile.gettempdir()) / "refiner_capstone_temp"
        temp_dir.mkdir(exist_ok=True)

    for input_file in input_files:
        try:
            print(f"\nProcessing: {input_file.name}")
            
            # If input is UNC path, copy to temp local location
            process_input = input_file
            if temp_dir and str(input_file).startswith(r"\\wsl.localhost"):
                process_input = temp_dir / input_file.name
                try:
                    shutil.copy2(str(input_file), str(process_input))
                except Exception as e:
                    print(f"  Note: Direct copy failed, trying WSL...")
                    try:
                        wsl_input = str(input_file).replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                        subprocess.run(
                            ['wsl', 'cp', wsl_input, str(process_input)],
                            capture_output=True,
                            check=True,
                            timeout=10
                        )
                    except Exception as e2:
                        failed.append((input_file.name, f"Copy failed: {str(e2)}"))
                        eprint(f"  ✗ Could not copy file: {e2}")
                        continue
            
            # Use temp dir as output if output is UNC
            process_output = temp_dir if output_is_unc and temp_dir else output_dir
            
            result = process_path(
                input_path=process_input,
                outdir=process_output,
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
                symmetry=False,
                symmetry_axis=None,
                symmetry_prefer='auto',
                symmetry_weld=False,
                symmetry_tolerance=1e-5,
                blender_fallback=config.conversion.blender_fallback,
                blender_exe=config.conversion.blender_exe,
                assimp_fallback=config.conversion.assimp_fallback,
                open3d_fallback=config.conversion.open3d_fallback,
                preconvert=config.conversion.preconvert,
                pre_repair=config.repair.pre_repair,
                unwrap_uv_with_blender=config.uv.unwrap_uv_with_blender,
                unwrap_attempts=config.uv.unwrap_attempts,
                uv_min_coverage=config.uv.min_coverage,
                uv_max_overlap_pct=config.uv.max_overlap_pct,
                uv_max_oob_pct=config.uv.max_oob_pct,
                unwrap_angle_limit=config.uv.angle_limit,
                unwrap_island_margin=config.uv.island_margin,
                unwrap_pack_margin=config.uv.pack_margin,
                aggressive_symmetry=False,
                cxprj_thickness=config.cxprj.thickness,
                cxprj_scale=config.cxprj.scale,
            )
            if result:
                # If output was local temp, copy back to capstone
                if output_is_unc and temp_dir:
                    result_path = Path(result)
                    if result_path.parent == temp_dir:
                        # Copy to capstone output
                        capstone_output = output_dir / result_path.name
                        try:
                            shutil.copy2(str(result_path), str(capstone_output))
                            result = str(capstone_output)
                        except Exception as e:
                            print(f"  Note: Direct copy failed, trying WSL...")
                            try:
                                wsl_output = str(output_dir).replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                                wsl_result = f"{wsl_output}/{result_path.name}"
                                subprocess.run(
                                    ['wsl', 'cp', str(result_path), wsl_result],
                                    capture_output=True,
                                    check=True,
                                    timeout=10
                                )
                                result = str(wsl_result)
                            except Exception as e2:
                                eprint(f"  ✗ Could not copy result: {e2}")
                
                processed.append((input_file.name, result))
                print(f"  ✓ Processed: {result}")
            else:
                failed.append((input_file.name, "Unknown error"))
                print(f"  ✗ Failed to process")
        except Exception as ex:
            failed.append((input_file.name, str(ex)))
            eprint(f"  ✗ Error: {ex}")
        finally:
            # Clean up temp input file if created
            if temp_dir and str(input_file).startswith(r"\\wsl.localhost"):
                process_input = temp_dir / input_file.name
                try:
                    if process_input.exists():
                        process_input.unlink()
                except Exception:
                    pass

    # Clean up temp directory
    if temp_dir and temp_dir.exists():
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    print(f"\n=== Processing Complete ===")
    print(f"Processed: {len(processed)}/{len(input_files)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for name, reason in failed:
            print(f"  - {name}: {reason}")

    return 0 if not failed else 1


def cmd_capstone_list_inputs(args) -> int:
    """List input files from capstone input directory."""
    import subprocess
    
    capstone_root = getattr(args, 'capstone_root', None)
    integration = RefinerCapstoneIntegration(capstone_root)

    files = integration.get_capstone_input_files()
    print(f"Input files ({len(files)} total):")
    for f in files:
        try:
            # Try to get file size via stat
            size_mb = f.stat().st_size / (1024 * 1024)
        except (FileNotFoundError, OSError):
            # If file is not directly accessible (UNC path), use WSL
            try:
                f_str = str(f)
                if f_str.startswith(r"\\wsl.localhost"):
                    wsl_path = f_str.replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                    result = subprocess.run(
                        ['wsl', 'stat', '-c', '%s', wsl_path],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        size_mb = int(result.stdout.strip()) / (1024 * 1024)
                    else:
                        size_mb = 0
                else:
                    size_mb = 0
            except Exception:
                size_mb = 0
        
        print(f"  {f.name:<40} ({size_mb:>8.2f} MB)")

    return 0


def cmd_capstone_convert_paths(args) -> int:
    """Convert paths between Windows and WSL formats."""
    path = getattr(args, 'path', None)
    if not path:
        eprint("No path provided")
        return 1

    print(f"\nPath Conversions:")
    print(f"Input:                    {path}")
    print(f"WSL path:                 {WSLPathConverter.to_wsl_path(path)}")
    print(f"Windows (UNC):            {WSLPathConverter.to_wsl_localhost_path(WSLPathConverter.to_wsl_path(path))}")
    print(f"\nDetected environment:     {WSLPathConverter.detect_environment()}")

    return 0


def add_capstone_subcommands(subparsers):
    """Add capstone subcommands to the main CLI parser."""
    
    p_capstone = subparsers.add_parser('capstone', help='Capstone project integration')
    p_capstone_sub = p_capstone.add_subparsers(dest='capstone_subcommand', help='Capstone commands')

    # Status command
    p_status = p_capstone_sub.add_parser('status', help='Show capstone integration status')
    p_status.add_argument('--capstone-root', type=str, default=None,
                         help='Path to capstone root directory')
    p_status.set_defaults(func=cmd_capstone_status)

    # List inputs command
    p_list = p_capstone_sub.add_parser('list-inputs', help='List input files from capstone')
    p_list.add_argument('--capstone-root', type=str, default=None,
                       help='Path to capstone root directory')
    p_list.set_defaults(func=cmd_capstone_list_inputs)

    # Process inputs command
    p_process = p_capstone_sub.add_parser('process-inputs', 
                                         help='Process all capstone input files through Refiner')
    p_process.add_argument('--capstone-root', type=str, default=None,
                          help='Path to capstone root directory')
    p_process.add_argument('-o', '--output-subdir', type=str, default='refined_meshes',
                          help='Output subdirectory within capstone outputs/ (default: refined_meshes)')
    # Add all standard processing arguments
    from .cli_v2 import _add_smoothing_args, _add_texture_args, _add_uv_args, _add_conversion_args, _add_cxprj_args, _add_repair_args
    _add_smoothing_args(p_process)
    _add_texture_args(p_process)
    _add_uv_args(p_process)
    _add_conversion_args(p_process)
    _add_cxprj_args(p_process)
    _add_repair_args(p_process)
    p_process.set_defaults(func=cmd_capstone_process_inputs)

    # Convert paths command
    p_convert = p_capstone_sub.add_parser('convert-paths', help='Convert between Windows/WSL paths')
    p_convert.add_argument('path', nargs='?', default=None, help='Path to convert')
    p_convert.set_defaults(func=cmd_capstone_convert_paths)

    return p_capstone
