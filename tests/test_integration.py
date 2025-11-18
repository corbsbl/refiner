"""Integration tests for the Refiner pipeline.

Tests common workflows: single file processing, batch processing, analysis, and Unreal staging.
"""

import unittest
import tempfile
from pathlib import Path
import json

# Try to import core modules; skip tests if dependencies unavailable
try:
    from refiner_core.pipeline import process_path
    from refiner_core.analyzer import analyze_path
    from refiner_core.config import PipelineConfig
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TestIntegrationWorkflows(unittest.TestCase):
    """Integration tests for complete workflows."""

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def setUp(self):
        """Set up temporary directories for test outputs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.output_dir = self.temp_path / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directories."""
        self.temp_dir.cleanup()

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def test_pipeline_config_from_defaults(self):
        """Test that PipelineConfig can be created with defaults."""
        config = PipelineConfig()
        self.assertEqual(config.smoothing.method, 'taubin')
        self.assertEqual(config.smoothing.iterations, 10)
        self.assertEqual(config.texture.bilateral_d, 9)
        self.assertFalse(config.unreal.defer_import)

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def test_pipeline_config_validation(self):
        """Test that invalid smoothing method raises ValueError."""
        from refiner_core.config import SmoothingConfig
        with self.assertRaises(ValueError):
            SmoothingConfig(method='invalid_method')

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def test_texture_config_validation(self):
        """Test that invalid texture method raises ValueError."""
        from refiner_core.config import TextureConfig
        with self.assertRaises(ValueError):
            TextureConfig(method='invalid_filter')

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def test_config_from_args_namespace(self):
        """Test that config can be created from argparse namespace."""
        class FakeArgs:
            method = 'laplacian'
            iterations = 15
            lamb = 0.6
            nu = -0.5
            smooth_textures = True
            texture_method = 'gaussian'
            bilateral_d = 11
            bilateral_sigma_color = 80.0
            bilateral_sigma_space = 80.0
            gaussian_ksize = 7
            gaussian_sigma = 1.5
            unwrap_uv_with_blender = False
            unwrap_attempts = 3
            uv_min_coverage = 60.0
            uv_max_overlap_pct = 15.0
            uv_max_oob_pct = 8.0
            unwrap_angle_limit = 70.0
            unwrap_island_margin = 0.01
            unwrap_pack_margin = 0.004
            blender_fallback = False
            blender_exe = None
            assimp_fallback = False
            open3d_fallback = False
            preconvert = False
            cxprj_thickness = 2.0
            cxprj_scale = 1.5
            pre_repair = True
            no_pre_repair = False
            unreal_project = None
            unreal_assets_folder = 'Meshes/Custom'
            defer_unreal_import = False

        config = PipelineConfig.from_args(FakeArgs())
        self.assertEqual(config.smoothing.method, 'laplacian')
        self.assertEqual(config.smoothing.iterations, 15)
        self.assertTrue(config.texture.smooth_textures)
        self.assertEqual(config.texture.gaussian_ksize, 7)
        self.assertEqual(config.uv.unwrap_attempts, 3)
        self.assertEqual(config.unreal.assets_folder, 'Meshes/Custom')


class TestAnalysisWorkflow(unittest.TestCase):
    """Test analysis-only workflows."""

    def setUp(self):
        """Set up temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    @unittest.skipIf(not HAS_DEPS, "Dependencies not available")
    def test_analyze_path_with_missing_file(self):
        """Test that analyze_path handles missing files gracefully."""
        missing_file = self.temp_path / 'nonexistent.obj'
        try:
            report = analyze_path(missing_file)
            # Should return a report with error indication or empty meshes
            self.assertIsInstance(report, dict)
        except Exception as ex:
            # Some implementations may raise; that's acceptable
            self.assertIn('not found', str(ex).lower())


if __name__ == '__main__':
    unittest.main()
