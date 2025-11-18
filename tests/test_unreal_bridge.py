import unittest
import tempfile
import os
from pathlib import Path
import time

from refiner_core.unreal_bridge import (
    validate_unreal_project,
    stage_to_deferred,
    finalize_deferred,
    stage_to_unreal,
)


class TestUnrealBridge(unittest.TestCase):
    def test_deferred_and_finalize_happy_path(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # Create a fake project structure
            project = td / 'MyGame'
            project.mkdir()
            uproject = project / 'MyGame.uproject'
            uproject.write_text('{}', encoding='utf-8')
            content = project / 'Content'
            content.mkdir()

            # Create a source glb
            src = td / 'sample.glb'
            src.write_text('glbdata', encoding='utf-8')

            # Stage to deferred
            deferred_glb, deferred_meta = stage_to_deferred(src, uproject)
            self.assertTrue(deferred_glb.exists())
            self.assertTrue(deferred_meta.exists())

            # Finalize into Content
            final_glb, final_meta = finalize_deferred(deferred_glb, uproject)
            self.assertTrue(final_glb.exists())
            self.assertTrue(final_meta.exists())

            # mtimes should be recent (within 10 seconds)
            now = time.time()
            self.assertTrue(abs(final_glb.stat().st_mtime - now) < 10)
            self.assertTrue(abs(final_meta.stat().st_mtime - now) < 10)

    def test_validate_project_missing_content(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            project = td / 'MyGame'
            project.mkdir()
            uproject = project / 'MyGame.uproject'
            uproject.write_text('{}', encoding='utf-8')
            # Do not create Content/
            ok = validate_unreal_project(uproject)
            self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
