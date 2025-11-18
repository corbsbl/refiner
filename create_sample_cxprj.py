#!/usr/bin/env python3
"""Generate a simple test CXPRJ file for smoke testing."""

from pathlib import Path
import zipfile
import tempfile
import shutil

# Create input directory if needed
input_dir = Path('input')
input_dir.mkdir(exist_ok=True)

# Create temporary directory for SVG
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    
    # Write a simple SVG: a square and a circle
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect x="20" y="20" width="80" height="80" fill="none" stroke="black" stroke-width="2"/>
  <circle cx="150" cy="70" r="40" fill="none" stroke="black" stroke-width="2"/>
  <path d="M 50 150 L 100 150 L 75 190 Z" fill="none" stroke="black" stroke-width="2"/>
</svg>'''
    
    svg_file = tmp_path / 'design.svg'
    svg_file.write_text(svg_content, encoding='utf-8')
    
    # Create CXPRJ (which is just a ZIP containing SVGs and metadata)
    cxprj_path = input_dir / 'test_sample.cxprj'
    
    with zipfile.ZipFile(cxprj_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        # Add the SVG
        archive.write(svg_file, arcname='design.svg')
        
        # Add a minimal metadata JSON (not strictly required, but realistic)
        metadata = '''{
  "version": "1.0",
  "name": "Test Sample",
  "layers": [
    {
      "id": "layer_1",
      "name": "Cut",
      "type": "cut",
      "visible": true,
      "asset": "design.svg"
    }
  ]
}'''
        archive.writestr('metadata.json', metadata)

print(f"✓ Created test CXPRJ: {cxprj_path}")
print(f"  File size: {cxprj_path.stat().st_size} bytes")
