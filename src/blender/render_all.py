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

# Polyhaven HDRI to download for studio environment lighting.
HDRI_ASSET_ID = "brown_photostudio_02"
HDRI_RESOLUTION = "1k"

# ---------------------------------------------------------------------------
# Material presets per component role
# ---------------------------------------------------------------------------

# Maps component names to material tweaks (roughness, metallic).
MATERIAL_OVERRIDES = {
    "Frame": {"roughness": 0.25, "metallic": 0.85},
    "PeelPlate": {"roughness": 0.35, "metallic": 0.7},
    "VialCradle": {"roughness": 0.55, "metallic": 0.0},
    "SpoolHolder": {"roughness": 0.55, "metallic": 0.0},
    "DancerArm": {"roughness": 0.45, "metallic": 0.1},
    "GuideRollerBracket": {"roughness": 0.50, "metallic": 0.0},
}

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
        help="Render sample count (default: 128)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Assembly import
# ---------------------------------------------------------------------------


def clear_scene():
    """Remove all existing objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
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

    # STL units are mm; scale to meters for Blender.
    obj.scale = (0.001, 0.001, 0.001)
    obj.location = Vector(location) * 0.001
    obj.rotation_euler = tuple(math.radians(r) for r in rotation)

    # Apply material with color and per-component properties.
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        overrides = MATERIAL_OVERRIDES.get(name, {})
        bsdf.inputs["Roughness"].default_value = overrides.get("roughness", 0.5)
        bsdf.inputs["Metallic"].default_value = overrides.get("metallic", 0.0)
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


def get_assembly_bounds(objects):
    """Return (center, size) bounding box of all objects in world space."""
    if not objects:
        return Vector((0, 0, 0)), Vector((0.1, 0.1, 0.1))

    bpy.context.view_layer.update()

    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            for i in range(3):
                min_corner[i] = min(min_corner[i], world_corner[i])
                max_corner[i] = max(max_corner[i], world_corner[i])

    center = (min_corner + max_corner) / 2
    size = max_corner - min_corner
    return center, size


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------


def setup_ground_plane(assembly_center):
    """Add a shadow-catcher ground plane below the assembly."""
    bpy.ops.mesh.primitive_plane_add(
        size=2.0, location=(assembly_center.x, assembly_center.y, 0.0)
    )
    plane = bpy.context.active_object
    plane.name = "GroundPlane"

    # Shadow catcher makes the plane invisible except for shadows.
    plane.is_shadow_catcher = True

    # Minimal diffuse material so it catches shadows cleanly.
    mat = bpy.data.materials.new(name="Mat_Ground")
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.95, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    plane.data.materials.append(mat)

    return plane


def setup_hdri_environment():
    """Set up a Polyhaven studio HDRI for environment lighting.

    Downloads the HDRI file via Blender's Polyhaven integration and wires
    it into the world shader. Falls back to 3-point lighting on failure.
    """
    hdri_path = _find_or_download_hdri()
    if not hdri_path:
        print("HDRI not available, falling back to 3-point lighting")
        setup_three_point_lighting()
        return

    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    # Environment texture -> Background -> Output
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(hdri_path)

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Strength"].default_value = 1.0

    output_node = nodes.new(type="ShaderNodeOutputWorld")

    links.new(env_tex.outputs["Color"], bg_node.inputs["Color"])
    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])
    print(f"HDRI environment loaded: {hdri_path}")


def _find_or_download_hdri():
    """Return a filesystem path to the HDRI, downloading if needed."""
    # Check Blender's Polyhaven cache first.
    prefs_dir = bpy.utils.resource_path("USER")
    cache_dir = os.path.join(prefs_dir, "datafiles", "studiolights", "world")

    # Also check common Polyhaven download locations.
    search_dirs = [
        cache_dir,
        os.path.join(PROJECT_ROOT, "assets", "hdri"),
        os.path.join(os.path.expanduser("~"), "polyhaven"),
    ]

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if HDRI_ASSET_ID in fname and fname.endswith((".hdr", ".exr")):
                return os.path.join(d, fname)

    # Try downloading via Blender's Polyhaven add-on preferences API.
    try:
        bpy.ops.world.polyhaven_download(
            asset_id=HDRI_ASSET_ID, resolution=HDRI_RESOLUTION
        )
        # Re-scan after download.
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if HDRI_ASSET_ID in fname and fname.endswith((".hdr", ".exr")):
                    return os.path.join(d, fname)
    except Exception as exc:
        print(f"Polyhaven download failed: {exc}")

    return None


def setup_three_point_lighting():
    """Fallback 3-point lighting when HDRI is unavailable."""
    # Key light - warm sun from upper right
    bpy.ops.object.light_add(type="SUN", location=(1.0, -0.5, 1.0))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 3.0
    key.data.color = (1.0, 0.95, 0.9)
    key.rotation_euler = (math.radians(45), math.radians(15), math.radians(-30))

    # Fill light - cool area light from opposite side
    bpy.ops.object.light_add(type="AREA", location=(-0.5, 0.5, 0.8))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 30.0
    fill.data.size = 1.5
    fill.data.color = (0.9, 0.92, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(135))

    # Rim light - accent from behind
    bpy.ops.object.light_add(type="AREA", location=(-0.2, 0.6, 0.5))
    rim = bpy.context.active_object
    rim.name = "RimLight"
    rim.data.energy = 40.0
    rim.data.size = 0.5
    rim.data.color = (1.0, 1.0, 1.0)
    rim.rotation_euler = (math.radians(30), 0, math.radians(200))

    # Neutral grey world background
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (0.85, 0.85, 0.85, 1.0)
    bg_node.inputs["Strength"].default_value = 0.3

    output_node = nodes.new(type="ShaderNodeOutputWorld")
    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


# ---------------------------------------------------------------------------
# Camera utilities
# ---------------------------------------------------------------------------


def look_at(camera_obj, target):
    """Point camera at target location."""
    direction = target - camera_obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    camera_obj.rotation_euler = rot_quat.to_euler()


def setup_camera(position, target, lens=50, dof_target=None):
    """Create or reuse a camera, position it, and point at target."""
    cam_data = bpy.data.cameras.get("RenderCam")
    if cam_data is None:
        cam_data = bpy.data.cameras.new("RenderCam")
    cam_data.lens = lens
    cam_data.clip_start = 0.01
    cam_data.clip_end = 100.0

    # Depth of field
    if dof_target is not None:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = (Vector(position) - Vector(dof_target)).length
        cam_data.dof.aperture_fstop = 4.0
    else:
        cam_data.dof.use_dof = False

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
    """Set up render engine: Cycles for quality, EEVEE for fast preview."""
    scene = bpy.context.scene

    use_cycles = samples >= 32
    if use_cycles:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.device = "CPU"
        # Transparent background for compositing flexibility
        scene.render.film_transparent = True
    else:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.taa_render_samples = max(samples, 16)
        scene.render.film_transparent = True

    # Parse resolution
    parts = resolution.split("x")
    if len(parts) != 2:
        print(f"ERROR: Invalid resolution '{resolution}', expected WxH")
        sys.exit(1)
    scene.render.resolution_x = int(parts[0])
    scene.render.resolution_y = int(parts[1])
    scene.render.resolution_percentage = 100

    # Output settings
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    engine_name = "Cycles" if use_cycles else "EEVEE"
    print(f"Render engine: {engine_name} ({samples} samples)")


# ---------------------------------------------------------------------------
# Camera presets (computed dynamically from assembly bounds)
# ---------------------------------------------------------------------------


def build_camera_presets(center, size):
    """Return camera presets scaled to actual assembly dimensions."""
    # Distance factor: pull camera back enough to frame the whole assembly.
    max_dim = max(size.x, size.y, size.z)
    d = max(max_dim * 3.0, 0.3)

    cx, cy, cz = center.x, center.y, center.z

    return {
        "hero": {
            "position": (cx + d * 0.7, cy - d * 0.6, cz + d * 0.45),
            "target": (cx, cy, cz),
            "lens": 50,
            "dof": True,
            "filename": "hero_shot.png",
        },
        "isometric": {
            "position": (cx + d * 0.58, cy - d * 0.58, cz + d * 0.58),
            "target": (cx, cy, cz),
            "lens": 80,
            "dof": False,
            "filename": "isometric_view.png",
        },
        "front": {
            "position": (cx, cy - d, cz + max_dim * 0.3),
            "target": (cx, cy, cz),
            "lens": 50,
            "dof": False,
            "filename": "front_view.png",
        },
        "side": {
            "position": (cx + d, cy, cz + max_dim * 0.3),
            "target": (cx, cy, cz),
            "lens": 50,
            "dof": False,
            "filename": "side_view.png",
        },
        "detail_peel": {
            # Close-up of peel plate area (offset toward peel plate position).
            "position": (cx + 0.12, cy - 0.15, cz + 0.06),
            "target": (0.093, 0.0, 0.020),
            "lens": 65,
            "dof": True,
            "filename": "detail_peel.png",
        },
        "top": {
            "position": (cx, cy, cz + d),
            "target": (cx, cy, cz),
            "lens": 50,
            "dof": False,
            "filename": "top_view.png",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f"Render settings: resolution={args.resolution}, samples={args.samples}")
    print(f"Output directory: {args.output}")

    # Clear and import
    clear_scene()
    objects = import_assembly()
    if not objects:
        print("ERROR: No objects imported, aborting render")
        sys.exit(1)

    # Compute assembly bounds for camera placement
    assembly_center, assembly_size = get_assembly_bounds(objects)
    print(f"Assembly center: {assembly_center}, size: {assembly_size}")

    # Scene setup
    setup_ground_plane(assembly_center)
    setup_hdri_environment()
    configure_render(args.resolution, args.samples)

    # Build camera presets relative to actual assembly
    presets = build_camera_presets(assembly_center, assembly_size)

    # Render each camera preset
    for name, preset in presets.items():
        print(f"Rendering {name} view...")
        dof_target = preset["target"] if preset.get("dof") else None
        setup_camera(
            preset["position"],
            preset["target"],
            lens=preset.get("lens", 50),
            dof_target=dof_target,
        )

        output_path = os.path.join(args.output, preset["filename"])
        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        print(f"  Saved: {output_path}")

    print("All renders complete.")


if __name__ == "__main__":
    main()
