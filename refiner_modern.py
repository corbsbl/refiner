"""Refiner: 3D Mesh Refinement & Unreal Engine Integration Pipeline.

Modern entry point for the CLI. Delegates to refiner_core.cli_v2 for subcommand handling.
"""

import sys
from refiner_core.cli_v2 import main

__version__ = '1.1.0'
__author__ = 'Refiner Development Team'


if __name__ == '__main__':
    sys.exit(main())
