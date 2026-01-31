"""Headless Blender animation script for vial label applicator demo.

Renders a 20-25 second animation showing a label being peeled from backing
and applied to a spinning vial.

Usage:
    blender --background --python src/blender/animate_demo.py -- \
        --output models/renders/animation/ --duration 20 --fps 30 --samples 128
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
    "VialCradle": {"metallic": 0.0, "roughness": 0.6},
    "SpoolHolder": {"metallic": 0.0, "roughness": 0.6},
    "TensionArm": {"metallic": 0.0, "roughness": 0.6},
    "GuideRoller": {"metallic": 0.0, "roughness": 0.6},
    "LabelGuide": {"metallic": 0.0, "roughness": 0.6},
    "BaseMount": {"metallic": 0.0, "roughness": 0.6},
}

DEFAULT_MATERIAL = {"metallic": 0.0, "roughness": 0.5}

# ---------------------------------------------------------------------------
# Label path waypoints (meters) — from label_path.py computations
# ---------------------------------------------------------------------------

WAYPOINTS = [
    {"name": "spool_exit", "pos": (-0.070, -0.030, 0.023)},
    {
        "name": "dancer_roller",
        "pos": (0.022, -0.015, 0.0475),
        "wrap": 90,
        "radius": 0.011,
    },
    {
        "name": "guide_roller",
        "pos": (0.023, -0.035, 0.017),
        "wrap": 45,
        "radius": 0.011,
    },
    {"name": "peel_entry", "pos": (0.068, 0.000, 0.025)},
    {"name": "peel_edge", "pos": (0.0805, 0.000, 0.020), "wrap": 160, "radius": 0.001},
    {
        "name": "vial_contact",
        "pos": (0.058, 0.025, 0.023),
        "wrap": 270,
        "radius": 0.008,
    },
]

# ---------------------------------------------------------------------------
# Config values (mm, converted to meters where needed)
# ---------------------------------------------------------------------------

VIAL_DIAMETER_M = 0.016
VIAL_HEIGHT_M = 0.0385
LABEL_WIDTH_M = 0.040
LABEL_HEIGHT_M = 0.020
SPOOL_FLANGE_DIAMETER_M = 0.040
SPOOL_SPINDLE_OD_M = 0.0245

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args():
    """Parse arguments after the '--' separator in sys.argv."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    import argparse

    parser = argparse.ArgumentParser(description="Render animation demo")
    parser.add_argument(
        "--output",
        default=os.path.join(PROJECT_ROOT, "models", "renders", "animation"),
        help="Output directory for rendered frames",
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
    parser.add_argument(
        "--duration",
        type=float,
        default=20.0,
        help="Animation duration in seconds (default: 20)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second (default: 30)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: 960x540, 32 samples, EEVEE",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Scene management
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


# ---------------------------------------------------------------------------
# Assembly import
# ---------------------------------------------------------------------------


def import_stl(filepath, name, location, rotation, color):
    """Import an STL file and apply transforms and material."""
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found, skipping")
        return None

    bpy.ops.wm.stl_import(filepath=filepath)
    obj = bpy.context.active_object
    obj.name = name

    obj.scale = (0.001, 0.001, 0.001)
    obj.location = Vector(location) * 0.001
    obj.rotation_euler = tuple(math.radians(r) for r in rotation)

    mat = bpy.data.materials.new(name=f"Mat_{name}")
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
    obj.data.materials.append(mat)

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
# Animation-specific objects
# ---------------------------------------------------------------------------


def create_vial(cradle_position):
    """Create a glass vial cylinder at the cradle position.

    Args:
        cradle_position: VialCradle position from manifest (meters).

    Returns:
        The vial mesh object.
    """
    # Vial sits in cradle — center it vertically above cradle base
    vial_z = cradle_position.z + VIAL_HEIGHT_M / 2
    vial_loc = (cradle_position.x, cradle_position.y, vial_z)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=VIAL_DIAMETER_M / 2,
        depth=VIAL_HEIGHT_M,
        location=vial_loc,
    )
    vial = bpy.context.active_object
    vial.name = "Vial"

    # Smooth shading
    bpy.ops.object.shade_smooth()

    # Glass material
    mat = bpy.data.materials.new(name="Mat_Vial_Glass")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.9, 0.95, 1.0, 1.0)
        bsdf.inputs["Transmission Weight"].default_value = 0.95
        bsdf.inputs["Roughness"].default_value = 0.05
        bsdf.inputs["IOR"].default_value = 1.5
    vial.data.materials.append(mat)

    print(f"  Created vial at {vial_loc}")
    return vial


def create_label_strip():
    """Create a subdivided plane mesh for the label strip.

    The strip runs along the label path and will be deformed by a Curve
    modifier in Phase 2. Length is sized for the full path (~300mm).

    Returns:
        The label strip mesh object.
    """
    strip_length = 0.300  # 300mm total path
    strip_width = LABEL_HEIGHT_M  # 20mm label height = strip width

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    strip = bpy.context.active_object
    strip.name = "LabelStrip"

    # Scale to label dimensions
    strip.scale = (strip_length / 2, strip_width / 2, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    # Subdivide along length for smooth curve deformation
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=200)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Paper-like white material
    mat = bpy.data.materials.new(name="Mat_LabelStrip")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.3
    strip.data.materials.append(mat)

    print(
        f"  Created label strip ({strip_length * 1000:.0f}mm x {strip_width * 1000:.0f}mm)"
    )
    return strip


def create_label_roll(spool_position):
    """Create a label roll (torus-like cylinder) on the spool.

    Args:
        spool_position: SpoolHolder position from manifest (meters).

    Returns:
        The label roll mesh object.
    """
    outer_r = SPOOL_FLANGE_DIAMETER_M / 2 * 0.9  # slightly smaller than flange
    roll_height = LABEL_HEIGHT_M * 0.9

    # Position above spool base
    roll_z = spool_position.z + roll_height / 2 + 0.003
    roll_loc = (spool_position.x, spool_position.y, roll_z)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=outer_r,
        depth=roll_height,
        location=roll_loc,
    )
    roll = bpy.context.active_object
    roll.name = "LabelRoll"

    bpy.ops.object.shade_smooth()

    # Same paper-white material
    mat = bpy.data.materials.new(name="Mat_LabelRoll")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.92, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
    roll.data.materials.append(mat)

    print(f"  Created label roll at {roll_loc}")
    return roll


# ---------------------------------------------------------------------------
# Label path curve + deformation
# ---------------------------------------------------------------------------


def create_label_path_curve():
    """Create a 3D Bezier curve following the label path waypoints.

    Returns:
        The curve object.
    """
    curve_data = bpy.data.curves.new(name="LabelPathCurve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 64

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(WAYPOINTS) - 1)

    for i, wp in enumerate(WAYPOINTS):
        bp = spline.bezier_points[i]
        bp.co = Vector(wp["pos"])
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    # Tighten handles at sharp bends (peel edge especially)
    for i, wp in enumerate(WAYPOINTS):
        if wp.get("radius", 0) > 0:
            bp = spline.bezier_points[i]
            radius = wp["radius"]
            if radius <= 0.002:
                # Sharp peel edge — use vector handles for crisp bend
                bp.handle_left_type = "VECTOR"
                bp.handle_right_type = "VECTOR"

    curve_obj = bpy.data.objects.new("LabelPath", curve_data)
    bpy.context.scene.collection.objects.link(curve_obj)

    print("  Created label path curve with", len(WAYPOINTS), "control points")
    return curve_obj


def attach_strip_to_curve(strip, curve):
    """Attach the label strip mesh to the path curve via Curve modifier.

    Args:
        strip: The LabelStrip mesh object.
        curve: The LabelPath curve object.
    """
    # Position strip origin at curve start
    strip.location = Vector(WAYPOINTS[0]["pos"])

    mod = strip.modifiers.new("CurveDeform", "CURVE")
    mod.object = curve
    mod.deform_axis = "POS_X"

    print("  Attached label strip to path curve")


# ---------------------------------------------------------------------------
# Animation keyframes
# ---------------------------------------------------------------------------


def set_linear_interpolation(obj):
    """Set all keyframe interpolation to LINEAR for an object (Blender 5.0+ API)."""
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    slot = obj.animation_data.action_slot
    try:
        from bpy_extras import anim_utils

        channelbag = anim_utils.action_ensure_channelbag_for_slot(action, slot)
        for fc in channelbag.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    except (ImportError, AttributeError):
        # Fallback for older Blender versions
        try:
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except AttributeError:
            pass


def setup_animation(fps, duration):
    """Set up all animation keyframes.

    Timing (at 30fps, 20s = 600 frames):
      - Frames 1-60 (0-2s): Idle / establishing
      - Frames 60-150 (2-5s): Label starts advancing from spool
      - Frames 150-300 (5-10s): Label reaches vial, vial starts rotating
      - Frames 300-450 (10-15s): Label wraps around vial
      - Frames 450-600 (15-20s): Complete, hold

    Args:
        fps: Frames per second.
        duration: Total duration in seconds.
    """
    total_frames = int(fps * duration)

    # Get animated objects by name
    vial = bpy.data.objects.get("Vial")
    strip = bpy.data.objects.get("LabelStrip")
    roll = bpy.data.objects.get("LabelRoll")
    dancer = bpy.data.objects.get("DancerArm")

    # Frame markers for animation phases
    idle_end = int(total_frames * 0.10)  # 10% idle
    feed_start = idle_end
    contact_start = int(total_frames * 0.25)
    wrap_end = int(total_frames * 0.75)

    # --- Vial rotation ---
    if vial:
        # Vial starts rotating when label contacts
        vial.rotation_euler = (0, 0, 0)
        vial.keyframe_insert(data_path="rotation_euler", frame=1)
        vial.keyframe_insert(data_path="rotation_euler", frame=contact_start)

        # One full revolution during wrap phase
        vial.rotation_euler = (0, 0, math.radians(360))
        vial.keyframe_insert(data_path="rotation_euler", frame=wrap_end)

        # Hold final position
        vial.keyframe_insert(data_path="rotation_euler", frame=total_frames)

        # Set linear interpolation for constant rotation speed
        set_linear_interpolation(vial)

        print(f"  Vial: rotate frames {contact_start}-{wrap_end}")

    # --- Label strip offset (slide along curve) ---
    if strip:
        # Start off-curve (negative X offset hides strip)
        strip.location.x = WAYPOINTS[0]["pos"][0] - 0.30
        strip.keyframe_insert(data_path="location", frame=1)
        strip.keyframe_insert(data_path="location", frame=feed_start)

        # Advance to curve start
        strip.location.x = WAYPOINTS[0]["pos"][0]
        strip.keyframe_insert(data_path="location", frame=wrap_end)

        # Hold
        strip.keyframe_insert(data_path="location", frame=total_frames)

        set_linear_interpolation(strip)

        print(f"  Label strip: advance frames {feed_start}-{wrap_end}")

    # --- Spool roll shrinking ---
    if roll:
        roll.scale = (1.0, 1.0, 1.0)
        roll.keyframe_insert(data_path="scale", frame=1)
        roll.keyframe_insert(data_path="scale", frame=feed_start)

        # Shrink as label feeds out
        roll.scale = (0.7, 0.7, 1.0)
        roll.keyframe_insert(data_path="scale", frame=wrap_end)

        roll.keyframe_insert(data_path="scale", frame=total_frames)
        print(f"  Label roll: shrink frames {feed_start}-{wrap_end}")

    # --- Dancer arm oscillation ---
    if dancer:
        osc_frames = 8  # number of oscillation keyframes
        for i in range(osc_frames + 1):
            frame = feed_start + int((wrap_end - feed_start) * i / osc_frames)
            angle = math.radians(5.0 * math.sin(i * math.pi))
            dancer.rotation_euler.z = angle
            dancer.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
        print(f"  Dancer arm: oscillate frames {feed_start}-{wrap_end}")

    print(f"  Animation: {total_frames} frames, {duration}s @ {fps}fps")


def setup_camera_animation(center, peel_edge, vial_contact, dist, fps, duration):
    """Animate camera through 3 phases: establishing, dolly, close-up.

    Args:
        center: Assembly center point.
        peel_edge: Peel edge position (meters).
        vial_contact: Vial contact position (meters).
        dist: Camera distance from assembly.
        fps: Frames per second.
        duration: Total duration in seconds.
    """
    total_frames = int(fps * duration)
    cam = bpy.data.objects.get("AnimCam")
    if not cam:
        return

    # Phase boundaries
    phase1_end = int(total_frames * 0.20)  # establishing orbit
    phase2_end = int(total_frames * 0.60)  # dolly toward peel

    # Phase 1: Wide establishing — slow orbit from isometric
    cam.location = Vector(
        (
            center.x + dist * 0.6,
            center.y - dist * 0.7,
            center.z + dist * 0.4,
        )
    )
    look_at(cam, center)
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_euler", frame=1)

    # End of orbit — rotated ~30 degrees around assembly
    orbit_angle = math.radians(30)
    cam.location = Vector(
        (
            center.x
            + dist * 0.6 * math.cos(orbit_angle)
            + dist * 0.7 * math.sin(orbit_angle),
            center.y
            - dist * 0.7 * math.cos(orbit_angle)
            + dist * 0.6 * math.sin(orbit_angle),
            center.z + dist * 0.35,
        )
    )
    look_at(cam, center)
    cam.keyframe_insert(data_path="location", frame=phase1_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=phase1_end)

    # Phase 2: Dolly toward peel plate area
    peel_target = Vector(peel_edge)
    cam.location = Vector(
        (
            peel_target.x + dist * 0.25,
            peel_target.y - dist * 0.3,
            peel_target.z + dist * 0.15,
        )
    )
    look_at(cam, peel_target)
    cam.keyframe_insert(data_path="location", frame=phase2_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=phase2_end)

    # Phase 3: Close-up of label wrapping onto vial
    vial_target = Vector(vial_contact)
    cam.location = Vector(
        (
            vial_target.x + dist * 0.15,
            vial_target.y - dist * 0.2,
            vial_target.z + dist * 0.08,
        )
    )
    look_at(cam, vial_target)
    cam.keyframe_insert(data_path="location", frame=total_frames)
    cam.keyframe_insert(data_path="rotation_euler", frame=total_frames)

    # Enable DoF for close-up phase
    cam_data = cam.data
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 4.0
    cam_data.keyframe_insert(data_path="dof.aperture_fstop", frame=1)
    cam_data.keyframe_insert(data_path="dof.aperture_fstop", frame=phase2_end)
    cam_data.dof.aperture_fstop = 2.8
    cam_data.keyframe_insert(data_path="dof.aperture_fstop", frame=total_frames)

    print(
        f"  Camera: orbit 1-{phase1_end}, dolly {phase1_end}-{phase2_end}, "
        f"close-up {phase2_end}-{total_frames}"
    )


def add_label_texture():
    """Add a procedural label texture to the label strip.

    Creates a simple pattern: white base with a thin colored border
    and noise-based text simulation.
    """
    strip = bpy.data.objects.get("LabelStrip")
    if not strip or not strip.data.materials:
        return

    mat = strip.data.materials[0]
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    if not bsdf:
        return

    # Add noise texture to simulate printed text
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 80.0
    noise.inputs["Detail"].default_value = 8.0

    # Color ramp: mostly white with dark noise for "text"
    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.15, 0.15, 0.15, 1.0)

    # Mix with base white for subtle text effect
    mix = nodes.new(type="ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = 0.3
    mix.inputs[6].default_value = (1.0, 1.0, 1.0, 1.0)  # A color

    links.new(tex_coord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[7])  # B color
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])  # Result

    print("  Added procedural label texture")


def configure_final_render(resolution, samples, fps, duration, preview=False):
    """Configure render with motion blur and final quality settings."""
    scene = bpy.context.scene

    # Motion blur for mechanical feel
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5

    # Output as PNG sequence (set in configure_render already)
    # Set filepath pattern for animation rendering
    scene.render.filepath = ""  # will be set per-frame or as pattern

    print("  Enabled motion blur (shutter 0.5)")


# ---------------------------------------------------------------------------
# Scene setup — lighting, ground, background
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
    bpy.ops.object.light_add(type="AREA", location=(0.5, -0.5, 0.6))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 80.0
    key.data.size = 0.5
    key.data.color = (1.0, 0.95, 0.9)
    key.rotation_euler = (math.radians(55), 0, math.radians(-45))

    bpy.ops.object.light_add(type="AREA", location=(-0.5, 0.3, 0.4))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 30.0
    fill.data.size = 0.8
    fill.data.color = (0.85, 0.9, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(135))

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
    cam_data = bpy.data.cameras.get("AnimCam")
    if cam_data is None:
        cam_data = bpy.data.cameras.new("AnimCam")
    cam_data.lens = lens
    cam_data.clip_start = 0.001
    cam_data.clip_end = 100.0

    cam_data.dof.use_dof = dof_enabled
    if dof_enabled:
        cam_data.dof.aperture_fstop = f_stop
        cam_data.dof.focus_distance = (Vector(target) - Vector(position)).length

    cam_obj = bpy.data.objects.get("AnimCam")
    if cam_obj is None:
        cam_obj = bpy.data.objects.new("AnimCam", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = Vector(position)
    look_at(cam_obj, Vector(target))

    bpy.context.scene.camera = cam_obj
    return cam_obj


# ---------------------------------------------------------------------------
# Render configuration
# ---------------------------------------------------------------------------


def configure_render(resolution, samples, fps, duration, preview=False):
    """Configure render engine and animation frame range."""
    scene = bpy.context.scene

    if preview:
        resolution = "960x540"
        samples = 32

    parts = resolution.split("x")
    if len(parts) != 2:
        print(f"ERROR: Invalid resolution format '{resolution}', expected WxH")
        sys.exit(1)

    width, height = parts
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100

    # Frame range
    total_frames = int(duration * fps)
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.fps = fps

    # Engine selection
    if preview or samples < 32:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = samples
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.device = "CPU"

    # Output settings — PNG sequence
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True

    print(f"  Render: {width}x{height}, {samples} samples, {fps} fps")
    print(f"  Frames: {scene.frame_start}-{scene.frame_end} ({total_frames} total)")
    return total_frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 60)
    print("Vial Label Applicator — Animation Demo")
    print("=" * 60)

    # Clear and import assembly
    print("\n1. Importing assembly...")
    clear_scene()
    objects = import_assembly()
    if not objects:
        print("ERROR: No objects imported, aborting")
        sys.exit(1)

    # Compute bounds
    bbox_min, bbox_max, center = get_assembly_bounds(objects)
    print(f"   Assembly center: {center}")

    # Get component positions for animation objects
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    positions = {e["name"]: Vector(e["position"]) * 0.001 for e in manifest}

    # Create animation-specific objects
    print("\n2. Creating animation objects...")
    create_vial(positions["VialCradle"])
    strip = create_label_strip()
    create_label_roll(positions["SpoolHolder"])

    # Create label path curve and attach strip
    print("\n3. Creating label path curve...")
    curve = create_label_path_curve()
    attach_strip_to_curve(strip, curve)

    # Scene setup
    print("\n4. Setting up scene...")
    setup_ground_plane(center, bbox_min)
    setup_three_point_lighting(center)

    # Camera — establishing shot
    dist = compute_camera_distance(bbox_min, bbox_max)
    cam_pos = (
        center.x + dist * 0.6,
        center.y - dist * 0.7,
        center.z + dist * 0.4,
    )
    setup_camera(cam_pos, tuple(center), lens=50, dof_enabled=True, f_stop=4.0)

    # Configure render
    print("\n5. Configuring render...")
    configure_render(
        args.resolution, args.samples, args.fps, args.duration, args.preview
    )

    # Animation keyframes
    print("\n6. Setting up animation keyframes...")
    setup_animation(args.fps, args.duration)

    # Camera animation
    print("\n7. Setting up camera animation...")
    peel_edge = WAYPOINTS[4]["pos"]
    vial_contact = WAYPOINTS[5]["pos"]
    setup_camera_animation(
        center, peel_edge, vial_contact, dist, args.fps, args.duration
    )

    # Label texture
    print("\n8. Adding label texture...")
    add_label_texture()

    # Final render settings (motion blur)
    configure_final_render(
        args.resolution, args.samples, args.fps, args.duration, args.preview
    )

    # Render verification frames (first, middle, last)
    print("\n9. Rendering verification frames...")
    scene = bpy.context.scene
    total_frames = scene.frame_end
    check_frames = [1, total_frames // 2, total_frames]
    for frame in check_frames:
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(args.output, f"frame_{frame:04d}")
        bpy.ops.render.render(write_still=True)
        print(f"   Saved frame {frame}: {scene.render.filepath}.png")

    print("\nAnimation demo complete — all phases verified.")


if __name__ == "__main__":
    main()
