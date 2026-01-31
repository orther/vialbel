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
# Material overrides per component type
# ---------------------------------------------------------------------------

MATERIAL_OVERRIDES = {
    "Frame": {"metallic": 0.8, "roughness": 0.25},
    "PeelPlate": {"metallic": 0.6, "roughness": 0.3},
    # Printed parts — matte PLA/ASA finish
    "VialCradle": {"metallic": 0.0, "roughness": 0.6},
    "SpoolHolder": {"metallic": 0.0, "roughness": 0.6},
    "TensionArm": {"metallic": 0.0, "roughness": 0.6},
    "GuideRoller": {"metallic": 0.0, "roughness": 0.6},
    "LabelGuide": {"metallic": 0.0, "roughness": 0.6},
    "BaseMount": {"metallic": 0.0, "roughness": 0.6},
}

# Default for parts not listed above
DEFAULT_MATERIAL = {"metallic": 0.0, "roughness": 0.5}

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


def apply_material_overrides(obj, name):
    """Apply material override properties based on component name."""
    overrides = DEFAULT_MATERIAL
    for key, props in MATERIAL_OVERRIDES.items():
        if key in name:
            overrides = props
            break

    if obj.data.materials:
        mat = obj.data.materials[0]
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Metallic"].default_value = overrides["metallic"]
            bsdf.inputs["Roughness"].default_value = overrides["roughness"]


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

    # Create material with color.
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
    obj.data.materials.append(mat)

    # Apply per-component overrides.
    apply_material_overrides(obj, name)

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


# ---------------------------------------------------------------------------
# Bounding box utilities
# ---------------------------------------------------------------------------


def get_assembly_bounds(objects):
    """Compute min/max corners and center of all objects in world space."""
    if not objects:
        zero = Vector((0, 0, 0))
        return zero, zero, zero

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
    return min_corner, max_corner, center


def compute_camera_distance(bbox_min, bbox_max, fov_deg=50.0, fill_fraction=0.7):
    """Compute distance so the assembly fills fill_fraction of the frame."""
    extent = bbox_max - bbox_min
    max_extent = max(extent.x, extent.y, extent.z)
    half_fov = math.radians(fov_deg / 2)
    distance = (max_extent / fill_fraction) / (2 * math.tan(half_fov))
    return max(distance, 0.1)


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------


def setup_ground_plane(assembly_center, bbox_min):
    """Add a shadow-catcher ground plane below the assembly."""
    bpy.ops.mesh.primitive_plane_add(
        size=2.0, location=(assembly_center.x, assembly_center.y, bbox_min.z)
    )
    plane = bpy.context.active_object
    plane.name = "GroundPlane"
    plane.is_shadow_catcher = True
    return plane


def setup_three_point_lighting(assembly_center):
    """Set up 3-point studio lighting: warm key, cool fill, rim."""
    # Key light — warm, 45 degrees front-right
    bpy.ops.object.light_add(type="AREA", location=(0.5, -0.5, 0.6))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 80.0
    key.data.size = 0.5
    key.data.color = (1.0, 0.95, 0.9)  # warm
    key.rotation_euler = (math.radians(55), 0, math.radians(-45))

    # Fill light — cool, opposite side
    bpy.ops.object.light_add(type="AREA", location=(-0.5, 0.3, 0.4))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 30.0
    fill.data.size = 0.8
    fill.data.color = (0.85, 0.9, 1.0)  # cool
    fill.rotation_euler = (math.radians(60), 0, math.radians(135))

    # Rim light — behind and above
    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.6, 0.5))
    rim = bpy.context.active_object
    rim.name = "RimLight"
    rim.data.energy = 60.0
    rim.data.size = 0.4
    rim.data.color = (1.0, 1.0, 1.0)
    rim.rotation_euler = (math.radians(120), 0, math.radians(180))

    # World background — procedural gradient sky
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    # Gradient: light grey top, white bottom
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    separate = nodes.new(type="ShaderNodeSeparateXYZ")
    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.95, 0.95, 0.97, 1.0)
    ramp.color_ramp.elements[1].color = (0.8, 0.82, 0.85, 1.0)

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Strength"].default_value = 0.3

    output_node = nodes.new(type="ShaderNodeOutputWorld")

    links.new(tex_coord.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg_node.inputs["Color"])
    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


# ---------------------------------------------------------------------------
# Camera utilities
# ---------------------------------------------------------------------------


def look_at(camera_obj, target):
    """Point camera at target location."""
    direction = target - camera_obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    camera_obj.rotation_euler = rot_quat.to_euler()


def setup_camera(position, target, lens=50, dof_enabled=False, f_stop=4.0):
    """Create or reuse a camera, position it, and point at target."""
    cam_data = bpy.data.cameras.get("RenderCam")
    if cam_data is None:
        cam_data = bpy.data.cameras.new("RenderCam")
    cam_data.lens = lens
    cam_data.clip_start = 0.001
    cam_data.clip_end = 100.0

    # Depth of field
    cam_data.dof.use_dof = dof_enabled
    if dof_enabled:
        cam_data.dof.aperture_fstop = f_stop
        cam_data.dof.focus_distance = (Vector(target) - Vector(position)).length

    cam_obj = bpy.data.objects.get("RenderCam")
    if cam_obj is None:
        cam_obj = bpy.data.objects.new("RenderCam", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = Vector(position)
    look_at(cam_obj, Vector(target))

    bpy.context.scene.camera = cam_obj
    return cam_obj


# ---------------------------------------------------------------------------
# Camera presets (built dynamically from assembly bounds)
# ---------------------------------------------------------------------------


def build_camera_presets(bbox_min, bbox_max, center):
    """Build 6 camera presets auto-fitted to the assembly bounding box."""
    dist = compute_camera_distance(bbox_min, bbox_max, fov_deg=50.0, fill_fraction=0.7)

    # Peel plate is roughly at front-bottom of assembly
    peel_target = Vector((center.x, bbox_min.y, center.z * 0.5))

    return {
        "hero": {
            "position": (
                center.x + dist * 0.6,
                center.y - dist * 0.7,
                center.z + dist * 0.4,
            ),
            "target": tuple(center),
            "lens": 50,
            "dof_enabled": True,
            "f_stop": 4.0,
            "filename": "hero_shot.png",
        },
        "isometric": {
            "position": (
                center.x + dist * 0.577,
                center.y - dist * 0.577,
                center.z + dist * 0.577,
            ),
            "target": tuple(center),
            "lens": 50,
            "filename": "isometric_view.png",
        },
        "front": {
            "position": (center.x, center.y - dist, center.z),
            "target": tuple(center),
            "lens": 50,
            "filename": "front_view.png",
        },
        "side": {
            "position": (center.x + dist, center.y, center.z),
            "target": tuple(center),
            "lens": 50,
            "filename": "side_view.png",
        },
        "top": {
            "position": (center.x, center.y, center.z + dist),
            "target": tuple(center),
            "lens": 50,
            "filename": "top_view.png",
        },
        "detail_peel": {
            "position": (
                peel_target.x + dist * 0.3,
                peel_target.y - dist * 0.4,
                peel_target.z + dist * 0.2,
            ),
            "target": tuple(peel_target),
            "lens": 85,
            "dof_enabled": True,
            "f_stop": 2.8,
            "filename": "detail_peel.png",
        },
    }


# ---------------------------------------------------------------------------
# Render configuration
# ---------------------------------------------------------------------------


def configure_render(resolution, samples):
    """Set up render engine — Cycles for samples >= 32, EEVEE otherwise."""
    scene = bpy.context.scene

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

    # Engine selection
    if samples >= 32:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.device = "CPU"
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = samples

    # Output settings — transparent film for shadow catcher compositing
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True


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

    # Compute assembly bounds
    bbox_min, bbox_max, center = get_assembly_bounds(objects)
    print(f"Assembly center: {center}")
    print(f"Assembly extents: {bbox_max - bbox_min}")

    # Scene setup
    setup_ground_plane(center, bbox_min)
    setup_three_point_lighting(center)
    configure_render(args.resolution, args.samples)

    # Build auto-fitted camera presets
    presets = build_camera_presets(bbox_min, bbox_max, center)

    # Render each view
    for name, preset in presets.items():
        print(f"Rendering {name} view...")
        setup_camera(
            preset["position"],
            preset["target"],
            lens=preset.get("lens", 50),
            dof_enabled=preset.get("dof_enabled", False),
            f_stop=preset.get("f_stop", 4.0),
        )

        output_path = os.path.join(args.output, preset["filename"])
        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        print(f"  Saved: {output_path}")

    print("All renders complete.")


if __name__ == "__main__":
    main()
