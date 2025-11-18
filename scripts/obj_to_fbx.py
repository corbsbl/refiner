#!/usr/bin/env python3
"""Blender headless script to convert OBJ to FBX."""

import bpy
import sys
from pathlib import Path

if len(sys.argv) < 4:
    print("Usage: blender --background --python script.py -- input.obj output.fbx [scale]")
    sys.exit(1)

input_obj = sys.argv[-3]
output_fbx = sys.argv[-2]
scale = float(sys.argv[-1]) if len(sys.argv) > 4 else 1.0

print(f"[Blender] Converting {input_obj} → {output_fbx} (scale={scale})")

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import OBJ - use the addon directly
try:
    # Enable the addon first
    bpy.ops.preferences.addon_enable(module="io_scene_obj")
    print("[Blender] Enabled io_scene_obj addon")
except:
    pass

# Import the OBJ file
try:
    ret = bpy.ops.import_scene.obj(filepath=input_obj)
    if ret != {'FINISHED'}:
        print(f"[Blender ERROR] OBJ import returned {ret}")
        sys.exit(1)
    print(f"[Blender] Imported {input_obj}")
except Exception as e:
    print(f"[Blender ERROR] Failed to import OBJ: {e}")
    sys.exit(1)

# Apply scale if specified
if scale != 1.0:
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            obj.scale = (scale, scale, scale)
    print(f"[Blender] Applied scale {scale}")

# Export as FBX
try:
    ret = bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=False,
        axis_forward='-Y',
        axis_up='Z'
    )
    if ret != {'FINISHED'}:
        print(f"[Blender ERROR] FBX export returned {ret}")
        sys.exit(1)
    
    if Path(output_fbx).exists():
        size = Path(output_fbx).stat().st_size
        print(f"[Blender] Exported FBX: {size} bytes")
    else:
        print(f"[Blender ERROR] FBX file not created")
        sys.exit(1)
except Exception as e:
    print(f"[Blender ERROR] FBX export exception: {e}")
    sys.exit(1)

print("[Blender] SUCCESS")
