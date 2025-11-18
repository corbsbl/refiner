"""WSL Integration Adapter for Refiner.

Bridges Refiner with the Gulfstream Generative AI Capstone project structure.
Handles WSL path conversion and capstone-specific workflows.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import json


class WSLPathConverter:
    """Convert between Windows, WSL, and Unix paths for capstone integration."""

    @staticmethod
    def to_wsl_path(windows_path: str) -> str:
        """Convert Windows path to WSL path.
        
        Example:
            C:\\Users\\chard\\OneDrive\\Desktop\\Refiner → /mnt/c/Users/chard/OneDrive/Desktop/Refiner
        """
        path = Path(windows_path).resolve()
        # Drive letter (e.g., C:) → /mnt/c
        drive = path.drive[0].lower() if path.drive else 'c'
        parts = list(path.parts[1:])  # Skip drive letter
        return f"/mnt/{drive}/" + "/".join(part.replace("\\", "/") for part in parts)

    @staticmethod
    def to_windows_path(wsl_path: str) -> str:
        """Convert WSL path to Windows path.
        
        Example:
            /mnt/c/Users/chard → C:\\Users\\chard
        """
        if not wsl_path.startswith("/mnt/"):
            return wsl_path
        parts = wsl_path[5:].split("/")
        drive = parts[0].upper() + ":"
        rest = "\\".join(parts[1:])
        return f"{drive}\\{rest}"

    @staticmethod
    def to_wsl_localhost_path(wsl_path: str) -> str:
        """Convert WSL path to \\wsl.localhost format for Windows access.
        
        Example:
            /home/corbino/Developer → \\\\wsl.localhost\\Ubuntu-22.04\\home\\corbino\\Developer
        """
        # Remove leading slash and convert to Windows UNC path
        return f"\\\\wsl.localhost\\Ubuntu-22.04\\{wsl_path.lstrip('/')}"

    @staticmethod
    def detect_environment() -> str:
        """Detect if running in WSL or Windows.
        
        Returns: 'wsl', 'windows', or 'unknown'
        """
        if sys.platform == 'linux':
            # Check if /proc/version mentions WSL
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower() or 'wsl' in f.read().lower():
                        return 'wsl'
            except Exception:
                pass
            return 'linux'
        elif sys.platform == 'win32':
            return 'windows'
        return 'unknown'


class CapstonePathsConfig:
    """Configuration for capstone project paths.
    
    IMPORTANT: When running Refiner in WSL environment, always use native WSL paths (/home/corbino/...)
    This avoids all UNC path issues and provides direct filesystem access.
    """

    def __init__(self, capstone_root: Optional[str] = None):
        """Initialize capstone paths.
        
        Args:
            capstone_root: Root path to capstone project. Auto-detected if None.
            
        Note:
            When running in WSL, uses native paths: /home/corbino/...
            When running on Windows, converts to UNC paths: \\wsl.localhost\Ubuntu-22.04\...
        """
        if capstone_root is None:
            # Auto-detect capstone root
            capstone_root = os.environ.get('CAPSTONE_ROOT')
            if not capstone_root:
                # Default to native WSL path (recommended approach)
                # When Refiner runs in WSL, this is the correct path
                capstone_root = '/home/corbino/Developer/REPO/2025Fall-Gulfstream-Generative-AI-Capstone'
        
        self.root = Path(capstone_root)
        self.input_dir = self.root / 'input'
        self.output_dir = self.root / 'outputs'
        self.backend_dir = self.root / 'backend'
        self.scripts_dir = self.root / 'scripts'
        self.models_cache_dir = self.root / 'models_cache'

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'root': str(self.root),
            'input': str(self.input_dir),
            'output': str(self.output_dir),
            'backend': str(self.backend_dir),
            'scripts': str(self.scripts_dir),
            'models_cache': str(self.models_cache_dir),
        }

    @staticmethod
    def validate(config: 'CapstonePathsConfig') -> Tuple[bool, str]:
        """Validate capstone directory structure.
        
        Returns: (is_valid, message)
        
        Note: When running Refiner in WSL, paths are directly accessible.
        """
        root_str = str(config.root)
        
        try:
            # Try direct path check first (works when running in WSL)
            if config.root.exists():
                if not config.input_dir.exists():
                    return False, f"Input directory not found: {config.input_dir}"
                if not config.output_dir.exists():
                    return False, f"Output directory not found: {config.output_dir}"
                return True, "Capstone paths validated successfully"
            else:
                return False, f"Capstone root not found: {config.root}"
        except Exception as e:
            return False, f"Error validating capstone paths: {str(e)}"


class RefinerCapstoneIntegration:
    """Integration layer between Refiner and Capstone."""

    def __init__(self, capstone_root: Optional[str] = None):
        """Initialize integration.
        
        Args:
            capstone_root: Path to capstone root directory.
        """
        self.paths = CapstonePathsConfig(capstone_root)
        self.converter = WSLPathConverter()
        self.environment = self.converter.detect_environment()

    def validate(self) -> Tuple[bool, str]:
        """Validate integration setup."""
        return CapstonePathsConfig.validate(self.paths)

    def get_capstone_input_files(self, extension: Optional[str] = None) -> list:
        """Get input files from capstone input directory.
        
        Args:
            extension: Filter by file extension (e.g., '.obj', '.glb'). If None, returns all.
            
        Returns:
            List of Path objects.
        """
        import subprocess
        
        input_dir_str = str(self.paths.input_dir)
        
        # Check if this is a UNC path (WSL accessible from Windows)
        if input_dir_str.startswith(r"\\wsl.localhost"):
            try:
                # Convert UNC path to WSL path for WSL command access
                # \\wsl.localhost\Ubuntu-22.04\home\corbino\... → /home/corbino/...
                wsl_path = input_dir_str.replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                
                # Use WSL to list files
                result = subprocess.run(
                    ['wsl', 'ls', '-1', wsl_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    files = []
                    for filename in result.stdout.strip().split('\n'):
                        if filename:
                            filepath = Path(input_dir_str) / filename
                            if extension is None or filename.lower().endswith(extension.lower()):
                                files.append(filepath)
                    return sorted(files)
            except Exception as e:
                print(f"Warning: Could not list WSL files: {e}")
                return []
        
        # Fall back to local path checking (running on Linux/WSL)
        try:
            if not self.paths.input_dir.exists():
                return []
            
            if extension:
                return sorted(self.paths.input_dir.glob(f"*{extension}"))
            else:
                return sorted([p for p in self.paths.input_dir.iterdir() if p.is_file()])
        except Exception as e:
            print(f"Warning: Could not list input files: {e}")
            return []

    def get_capstone_output_dir(self, subdirectory: Optional[str] = None) -> Path:
        """Get output directory path.
        
        Args:
            subdirectory: Optional subdirectory within outputs/ (e.g., 'refined_meshes').
            
        Returns:
            Path to output directory.
        """
        import subprocess
        
        if subdirectory:
            path = self.paths.output_dir / subdirectory
        else:
            path = self.paths.output_dir
        
        path_str = str(path)
        
        # Check if this is a UNC path (WSL accessible from Windows)
        if path_str.startswith(r"\\wsl.localhost"):
            try:
                # Convert UNC path to WSL path for mkdir command
                wsl_path = path_str.replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                
                # Use WSL to create directory
                subprocess.run(
                    ['wsl', 'mkdir', '-p', wsl_path],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                return path
            except Exception as e:
                print(f"Warning: Could not create output dir via WSL: {e}")
                # Try local mkdir as fallback
        
        # Try local mkdir
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create output dir: {e}")
        
        return path

    def create_integration_manifest(self, output_path: Optional[Path] = None) -> dict:
        """Create manifest for integration information.
        
        Args:
            output_path: Optional path to save manifest JSON.
            
        Returns:
            Manifest dictionary.
        """
        manifest = {
            'integration': 'Refiner-Capstone',
            'version': '1.0.0',
            'environment': self.environment,
            'paths': self.paths.to_dict(),
            'timestamp': str(Path(__file__).stat().st_mtime),
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

        return manifest

    def process_capstone_file_with_fallback(self, input_file: Path, output_dir: Path, process_func, **kwargs) -> Optional[Path]:
        """Process a capstone input file, handling UNC path limitations.
        
        When running on Windows with WSL capstone paths, this creates a temporary
        local copy of the input file, processes it, then copies output back to capstone.
        
        Args:
            input_file: Path to input file (may be UNC path)
            output_dir: Path to output directory (may be UNC path)
            process_func: Function to call with (input_path, output_path, **kwargs)
            **kwargs: Arguments to pass to process_func
            
        Returns:
            Path to processed output file, or None if failed
        """
        import tempfile
        import shutil
        import subprocess
        
        input_str = str(input_file)
        output_str = str(output_dir)
        
        # Check if we're dealing with UNC paths
        is_unc_input = input_str.startswith(r"\\wsl.localhost")
        is_unc_output = output_str.startswith(r"\\wsl.localhost")
        
        if is_unc_input or is_unc_output:
            # We need to use temporary local files
            temp_dir = Path(tempfile.gettempdir()) / "refiner_capstone_temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Copy input file locally if it's a UNC path
            if is_unc_input:
                local_input = temp_dir / input_file.name
                try:
                    shutil.copy2(str(input_file), str(local_input))
                except Exception as e:
                    print(f"Error copying input file locally: {e}")
                    # Try WSL copy instead
                    try:
                        wsl_input = input_str.replace(r"\\wsl.localhost\Ubuntu-22.04", "").replace("\\", "/")
                        subprocess.run(
                            ['wsl', 'cp', wsl_input, str(local_input)],
                            capture_output=True,
                            check=True,
                            timeout=10
                        )
                    except Exception as e2:
                        print(f"Error copying via WSL: {e2}")
                        return None
            else:
                local_input = input_file
            
            # Process using local files
            try:
                result = process_func(local_input, output_dir, **kwargs)
                if not result:
                    return None
                
                # Result should be the output path
                return Path(result) if result else None
                    
            finally:
                # Clean up temporary files
                try:
                    if is_unc_input and local_input.exists():
                        local_input.unlink()
                except Exception:
                    pass
        else:
            # Local paths - process directly
            return process_func(input_file, output_dir, **kwargs)

    def log_integration_status(self) -> str:
        """Generate integration status report.
        
        Returns:
            Status string.
        """
        is_valid, msg = self.validate()
        status = f"""
=== Refiner-Capstone Integration Status ===

Environment: {self.environment}
Validation: {'✓ PASS' if is_valid else '✗ FAIL'} - {msg}

Paths:
  Root:         {self.paths.root}
  Input:        {self.paths.input_dir}
  Output:       {self.paths.output_dir}
  Backend:      {self.paths.backend_dir}
  Scripts:      {self.paths.scripts_dir}
  Models Cache: {self.paths.models_cache_dir}

Input Files Available:
"""
        input_files = self.get_capstone_input_files()
        if input_files:
            for f in input_files[:5]:
                status += f"\n  - {f.name}"
            if len(input_files) > 5:
                status += f"\n  ... and {len(input_files) - 5} more"
        else:
            status += "\n  (none)"

        return status


def main():
    """CLI for testing integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Refiner-Capstone Integration')
    parser.add_argument('--capstone-root', type=str, default=None,
                        help='Path to capstone root directory')
    parser.add_argument('--validate', action='store_true',
                        help='Validate integration setup')
    parser.add_argument('--status', action='store_true',
                        help='Print integration status')
    parser.add_argument('--list-inputs', action='store_true',
                        help='List input files available')
    parser.add_argument('--manifest', type=str, default=None,
                        help='Create integration manifest at path')
    parser.add_argument('--to-wsl-path', type=str, default=None,
                        help='Convert Windows path to WSL')
    parser.add_argument('--to-windows-path', type=str, default=None,
                        help='Convert WSL path to Windows')
    
    args = parser.parse_args()

    integration = RefinerCapstoneIntegration(args.capstone_root)

    if args.to_wsl_path:
        print(f"Windows: {args.to_wsl_path}")
        print(f"WSL:     {WSLPathConverter.to_wsl_path(args.to_wsl_path)}")
        return 0

    if args.to_windows_path:
        print(f"WSL:     {args.to_windows_path}")
        print(f"Windows: {WSLPathConverter.to_windows_path(args.to_windows_path)}")
        return 0

    if args.validate:
        is_valid, msg = integration.validate()
        print(f"Validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
        print(f"Message: {msg}")
        return 0 if is_valid else 1

    if args.status:
        print(integration.log_integration_status())
        return 0

    if args.list_inputs:
        files = integration.get_capstone_input_files()
        print(f"Input files ({len(files)} total):")
        for f in files:
            print(f"  {f.name}")
        return 0

    if args.manifest:
        manifest = integration.create_integration_manifest(Path(args.manifest))
        print(f"Manifest created: {args.manifest}")
        print(json.dumps(manifest, indent=2))
        return 0

    # Default: print status
    print(integration.log_integration_status())
    return 0


if __name__ == '__main__':
    sys.exit(main())
