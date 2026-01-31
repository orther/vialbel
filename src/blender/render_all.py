"""Headless Blender render script for vial label applicator assembly.

Usage:
    blender --background --python src/blender/render_all.py -- \
        --output models/renders/ --resolution 1920x1080 --samples 128
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
COMPONENTS_DIR = os.path.join(PROJECT_ROOT, "models", "components")
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "models", "assembly_manifest.json")

# ---------------------------------------------------------------------------
# CLI argument parsing (after Blender's -- separator)
# ---------------------------------------------------------------------------


def parse_args():
    """Parse arguments after the '--' separator in sys.argv."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    import argparse

    parser = argparse.ArgumentParser(description="Render assembly views")
    parser.add_argument(
        "--output",
        default=os.path.join(PROJECT_ROOT, "models", "renders"),
        help="Output directory for rendered images",
    )
    parser.add_argument(
        "--resolution",
        default="1920x1080",
        help="Render resolution as WxH (default: 1920x1080)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=128,
        help="Cycles sample count (default: 128)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Assembly import (reuses logic from import_assembly.py)
# ---------------------------------------------------------------------------


def clear_scene():
    """Remove all existing objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # Also remove orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def import_stl(filepath, name, location, rotation, color):
    """Import an STL file and apply transforms and material."""
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found, skipping")
        return None

    bpy.ops.wm.stl_import(filepath=filepath)
    obj = bpy.context.active_object
    obj.name = name

    # STL units are mm; convert to meters for Blender.
    obj.location = Vector(location) * 0.001
    obj.rotation_euler = tuple(math.radians(r) for r in rotation)

    # Apply material with color.
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.5
    obj.data.materials.append(mat)

    return obj


def import_assembly():
    """Import all components from the assembly manifest."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    imported = []
    for entry in manifest:
        filepath = os.path.join(COMPONENTS_DIR, entry["file"])
        obj = import_stl(
            filepath,
            entry["name"],
            tuple(entry["position"]),
            tuple(entry["rotation"]),
            tuple(entry["color"]),
        )
        if obj:
            imported.append(obj)

    print(f"Imported {len(imported)}/{len(manifest)} components")
    return imported


def get_assembly_center(objects):
    """Compute the bounding box center of all imported objects."""
    if not objects:
        return Vector((0, 0, 0))

    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            for i in range(3):
                min_corner[i] = min(min_corner[i], world_corner[i])
                max_corner[i] = max(max_corner[i], world_corner[i])

    return (min_corner + max_corner) / 2


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------


def setup_ground_plane(assembly_center):
    """Add a ground plane below the assembly for shadow catching."""
    bpy.ops.mesh.primitive_plane_add(
        size=2.0, location=(assembly_center.x, assembly_center.y, 0.0)
    )
    plane = bpy.context.active_object
    plane.name = "GroundPlane"

    mat = bpy.data.materials.new(name="Mat_Ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    plane.data.materials.append(mat)

    return plane


def setup_lighting():
    """Add sun lamp and area light for studio-style lighting."""
    # Sun lamp — key light
    bpy.ops.object.light_add(type="SUN", location=(1.0, -0.5, 1.0))
    sun = bpy.context.active_object
    sun.name = "SunLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(-30))

    # Area light — fill light
    bpy.ops.object.light_add(type="AREA", location=(-0.5, 0.5, 0.8))
    area = bpy.context.active_object
    area.name = "FillLight"
    area.data.energy = 50.0
    area.data.size = 1.0
    area.rotation_euler = (math.radians(60), 0, math.radians(135))

    # World background — neutral grey
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear existing nodes
    nodes.clear()

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    bg_node.inputs["Strength"].default_value = 0.5

    output_node = nodes.new(type="ShaderNodeOutputWorld")

    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


# ---------------------------------------------------------------------------
# Camera utilities
# ---------------------------------------------------------------------------


def look_at(camera_obj, target):
    """Point camera at target location using mathutils."""
    direction = target - camera_obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    camera_obj.rotation_euler = rot_quat.to_euler()


def setup_camera(position, target):
    """Create or reuse a camera, position it, and point at target."""
    cam_data = bpy.data.cameras.get("RenderCam")
    if cam_data is None:
        cam_data = bpy.data.cameras.new("RenderCam")
    cam_data.lens = 50
    cam_data.clip_start = 0.01
    cam_data.clip_end = 100.0

    cam_obj = bpy.data.objects.get("RenderCam")
    if cam_obj is None:
        cam_obj = bpy.data.objects.new("RenderCam", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = Vector(position)
    look_at(cam_obj, Vector(target))

    bpy.context.scene.camera = cam_obj
    return cam_obj


# ---------------------------------------------------------------------------
# Render configuration
# ---------------------------------------------------------------------------


def configure_render(resolution, samples):
    """Set up Cycles render engine with denoising."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"

    # Parse resolution
    parts = resolution.split("x")
    if len(parts) != 2:
        print(
            f"ERROR: Invalid resolution format '{resolution}', expected WxH (e.g., 1920x1080)"
        )
        sys.exit(1)
    width, height = parts
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100

    # Cycles settings
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"

    # Use CPU for headless (GPU may not be available)
    scene.cycles.device = "CPU"

    # Output settings
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False


# ---------------------------------------------------------------------------
# Camera presets
# ---------------------------------------------------------------------------

CAMERA_PRESETS = {
    "hero": {
        "position": (0.25, -0.22, 0.18),
        "filename": "hero_shot.png",
    },
    "top": {
        "position": (0.0, 0.0, 0.4),
        "filename": "top_view.png",
    },
    "front": {
        "position": (0.0, -0.3, 0.08),
        "filename": "front_detail.png",
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)

    print(f"Render settings: resolution={args.resolution}, samples={args.samples}")
    print(f"Output directory: {args.output}")

    # Clear and import
    clear_scene()
    objects = import_assembly()
    if not objects:
        print("ERROR: No objects imported, aborting render")
        sys.exit(1)

    # Compute assembly center for camera look-at target
    assembly_center = get_assembly_center(objects)
    print(f"Assembly center: {assembly_center}")

    # Scene setup
    setup_ground_plane(assembly_center)
    setup_lighting()
    configure_render(args.resolution, args.samples)

    # Render each camera preset
    for name, preset in CAMERA_PRESETS.items():
        print(f"Rendering {name} view...")
        setup_camera(preset["position"], assembly_center)

        output_path = os.path.join(args.output, preset["filename"])
        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        print(f"  Saved: {output_path}")

    print("All renders complete.")


if __name__ == "__main__":
    main()
