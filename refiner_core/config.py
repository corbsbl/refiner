"""Pipeline configuration dataclasses.

This module provides a structured way to pass parameters through the pipeline,
reducing function signature bloat and improving maintainability.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SmoothingConfig:
    """Mesh smoothing parameters."""
    method: str = 'taubin'
    iterations: int = 10
    lamb: float = 0.5
    nu: float = -0.53

    def __post_init__(self):
        if self.method not in ('taubin', 'laplacian'):
            raise ValueError(f"Unknown smoothing method: {self.method}")


@dataclass
class TextureConfig:
    """Texture smoothing parameters."""
    smooth_textures: bool = False
    method: str = 'bilateral'
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0
    gaussian_ksize: int = 5
    gaussian_sigma: float = 1.2

    def __post_init__(self):
        if self.method not in ('bilateral', 'gaussian'):
            raise ValueError(f"Unknown texture method: {self.method}")


@dataclass
class UVConfig:
    """UV unwrapping and validation parameters."""
    unwrap_uv_with_blender: bool = False
    unwrap_attempts: int = 2
    min_coverage: float = 50.0
    max_overlap_pct: float = 10.0
    max_oob_pct: float = 5.0
    angle_limit: float = 66.0
    island_margin: float = 0.02
    pack_margin: float = 0.003


@dataclass
class RepairConfig:
    """Mesh repair parameters."""
    pre_repair: bool = True
    weld_tolerance: float = 1e-5


@dataclass
class PipelineConfig:
    """Complete pipeline configuration combining all sub-configs."""
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    texture: TextureConfig = field(default_factory=TextureConfig)
    uv: UVConfig = field(default_factory=UVConfig)
    repair: RepairConfig = field(default_factory=RepairConfig)

    @classmethod
    def from_args(cls, args) -> 'PipelineConfig':
        """Create a PipelineConfig from CLI args namespace."""
        return cls(
            smoothing=SmoothingConfig(
                method=getattr(args, 'method', 'taubin'),
                iterations=getattr(args, 'iterations', 10),
                lamb=getattr(args, 'lamb', 0.5),
                nu=getattr(args, 'nu', -0.53),
            ),
            texture=TextureConfig(
                smooth_textures=getattr(args, 'smooth_textures', False),
                method=getattr(args, 'texture_method', 'bilateral'),
                bilateral_d=getattr(args, 'bilateral_d', 9),
                bilateral_sigma_color=getattr(args, 'bilateral_sigma_color', 75.0),
                bilateral_sigma_space=getattr(args, 'bilateral_sigma_space', 75.0),
                gaussian_ksize=getattr(args, 'gaussian_ksize', 5),
                gaussian_sigma=getattr(args, 'gaussian_sigma', 1.2),
            ),
            uv=UVConfig(
                unwrap_uv_with_blender=getattr(args, 'unwrap_uv_with_blender', False),
                unwrap_attempts=getattr(args, 'unwrap_attempts', 2),
                min_coverage=getattr(args, 'uv_min_coverage', 50.0),
                max_overlap_pct=getattr(args, 'uv_max_overlap_pct', 10.0),
                max_oob_pct=getattr(args, 'uv_max_oob_pct', 5.0),
                angle_limit=getattr(args, 'unwrap_angle_limit', 66.0),
                island_margin=getattr(args, 'unwrap_island_margin', 0.02),
                pack_margin=getattr(args, 'unwrap_pack_margin', 0.003),
            ),
            repair=RepairConfig(
                pre_repair=(False if getattr(args, 'no_pre_repair', False) else True),
            ),
        )
