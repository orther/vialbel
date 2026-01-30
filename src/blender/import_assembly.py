"""Import all vial label applicator STL components into Blender at correct positions.

Designed to be executed via blender-mcp's execute_blender_code tool.
Expects STL files in models/components/ relative to the project root.
"""

import bpy
import os
from mathutils import Vector

# Project root — adjust if running from a different location.
PROJECT_ROOT = os.path.expanduser("~/code/vial-laybell")
COMPONENTS_DIR = os.path.join(PROJECT_ROOT, "models", "components")

# Component positions (matching frame.py layout, origin at base plate center).
# Each entry: (filename, location_xyz_mm, rotation_euler_deg, display_color_rgba)
COMPONENTS = [
    {
        "file": "main_frame.stl",
        "location": (0, 0, 0),
        "rotation": (0, 0, 0),
        "color": (0.6, 0.6, 0.6, 1.0),  # grey
        "name": "Frame",
    },
    {
        "file": "peel_plate.stl",
        "location": (62.0, 0, 20.0),  # near peel wall
        "rotation": (0, 0, 0),
        "color": (0.2, 0.5, 0.8, 1.0),  # blue
        "name": "PeelPlate",
    },
    {
        "file": "vial_cradle.stl",
        "location": (27.0, 25.0, 5.0),  # adjacent to peel plate
        "rotation": (0, 0, 0),
        "color": (0.8, 0.4, 0.2, 1.0),  # orange
        "name": "VialCradle",
    },
    {
        "file": "spool_holder.stl",
        "location": (-70.0, -30.0, 5.0),  # back-left
        "rotation": (0, 0, 0),
        "color": (0.3, 0.7, 0.3, 1.0),  # green
        "name": "SpoolHolder",
    },
    {
        "file": "dancer_arm.stl",
        "location": (-20.0, -25.0, 45.0),  # on pivot post
        "rotation": (0, 0, 0),
        "color": (0.7, 0.2, 0.5, 1.0),  # purple
        "name": "DancerArm",
    },
    {
        "file": "guide_roller_bracket.stl",
        "location": (-7.0, -35.0, 5.0),  # between dancer and peel
        "rotation": (0, 0, 0),
        "color": (0.8, 0.8, 0.2, 1.0),  # yellow
        "name": "GuideRollerBracket",
    },
]


def clear_scene():
    """Remove all existing mesh objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_stl(filepath, name, location, rotation, color):
    """Import an STL file and apply transforms and material."""
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found, skipping")
        return None

    bpy.ops.wm.stl_import(filepath=filepath)
    obj = bpy.context.active_object
    obj.name = name

    # STL units are mm, Blender default is meters. Scale 1:1 (mm mode).
    # Position in mm coordinates.
    obj.location = Vector(location) * 0.001  # convert mm to m
    obj.rotation_euler = tuple(r * 3.14159 / 180 for r in rotation)

    # Apply material with color.
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.5
    obj.data.materials.append(mat)

    return obj


def setup_assembly():
    """Import all components and arrange in assembly."""
    clear_scene()

    imported = []
    for comp in COMPONENTS:
        filepath = os.path.join(COMPONENTS_DIR, comp["file"])
        obj = import_stl(
            filepath,
            comp["name"],
            comp["location"],
            comp["rotation"],
            comp["color"],
        )
        if obj:
            imported.append(obj)

    print(f"Imported {len(imported)}/{len(COMPONENTS)} components")
    return imported


if __name__ == "__main__" or True:  # always run when executed via MCP
    setup_assembly()
