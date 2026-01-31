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
VIAL_RADIUS_M = VIAL_DIAMETER_M / 2
VIAL_HEIGHT_M = 0.0385
LABEL_WIDTH_M = 0.040
LABEL_HEIGHT_M = 0.020
SPOOL_FLANGE_DIAMETER_M = 0.040
SPOOL_SPINDLE_OD_M = 0.0245

# Derived from config.toml: base_thickness=5mm, cradle_v_block_height=18mm
BASE_THICKNESS_M = 0.005
CRADLE_V_BLOCK_HEIGHT_M = 0.018
VIAL_CENTER_Z = BASE_THICKNESS_M + CRADLE_V_BLOCK_HEIGHT_M  # 0.023m

# Assembly manifest positions (mm→m)
CRADLE_POS = Vector((0.058, 0.025, 0.005))
VIAL_CENTER = Vector((0.058, 0.025, VIAL_CENTER_Z))

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

# Peel edge position — the critical separation point
PEEL_EDGE_POS = Vector(WAYPOINTS[4]["pos"])
VIAL_CONTACT_POS = Vector(WAYPOINTS[5]["pos"])


def create_vial():
    """Create a glass vial cylinder above the cradle (will animate drop-in).

    The vial lies on its side (Y-axis) to sit in the V-block cradle.
    Position derived from VIAL_CENTER (assembly manifest + config).

    Returns:
        The vial mesh object positioned above the cradle for drop-in animation.
    """
    # Start position: above final resting position for drop-in
    start_z = VIAL_CENTER.z + 0.06  # 60mm above final position
    vial_loc = (VIAL_CENTER.x, VIAL_CENTER.y, start_z)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=VIAL_RADIUS_M,
        depth=VIAL_HEIGHT_M,
        location=vial_loc,
    )
    vial = bpy.context.active_object
    vial.name = "Vial"

    # Rotate to lie on side — cylinder axis along Y (into the V-block)
    vial.rotation_euler = (math.radians(90), 0, 0)

    for face in vial.data.polygons:
        face.use_smooth = True

    # Store final Z position as custom property for animation
    vial["final_z"] = VIAL_CENTER.z

    # Glass material — visible but translucent
    mat = bpy.data.materials.new(name="Mat_Vial_Glass")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.9, 0.95, 1.0)
        bsdf.inputs["Transmission Weight"].default_value = 0.3
        bsdf.inputs["Roughness"].default_value = 0.1
        bsdf.inputs["IOR"].default_value = 1.5
        bsdf.inputs["Alpha"].default_value = 0.6
    vial.data.materials.append(mat)

    print(f"  Created vial at ({VIAL_CENTER.x*1000:.0f}, "
          f"{VIAL_CENTER.y*1000:.0f}, {VIAL_CENTER.z*1000:.0f})mm, "
          f"start Z={start_z*1000:.0f}mm")
    return vial


def create_composite_feed():
    """Create the composite label+backing strip that follows the feed path.

    This represents the combined material from spool to peel edge:
    backing paper with labels printed on it. Built as a subdivided strip
    mesh (no edit mode needed) with a Curve modifier to follow the path.

    Returns:
        The composite feed mesh object.
    """
    feed_length = 0.350  # extra length so strip can advance into view
    feed_width = LABEL_HEIGHT_M  # 20mm
    segments = 120  # lengthwise subdivisions for smooth deformation

    # Build strip mesh from vertices (avoids edit mode subdivide)
    verts = []
    faces = []
    half_w = feed_width / 2
    for i in range(segments + 1):
        x = (i / segments) * feed_length
        verts.append((x, -half_w, 0))
        verts.append((x, half_w, 0))
    for i in range(segments):
        v0 = i * 2
        faces.append((v0, v0 + 2, v0 + 3, v0 + 1))

    mesh = bpy.data.meshes.new("CompositeFeedMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    feed = bpy.data.objects.new("CompositeFeed", mesh)
    bpy.context.scene.collection.objects.link(feed)

    # Two-tone material: white backing with colored label rectangles
    mat = bpy.data.materials.new(name="Mat_CompositeFeed")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
        tex_coord = nodes.new(type="ShaderNodeTexCoord")
        mapping = nodes.new(type="ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (8.75, 1.0, 1.0)

        wave = nodes.new(type="ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 1.0
        wave.inputs["Distortion"].default_value = 0.0
        wave.inputs["Detail"].default_value = 0.0

        ramp = nodes.new(type="ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (0.95, 0.95, 0.92, 1.0)
        ramp.color_ramp.elements[1].position = 0.4
        ramp.color_ramp.elements[1].color = (0.2, 0.6, 0.9, 1.0)

        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bsdf.inputs["Roughness"].default_value = 0.3

    feed.data.materials.append(mat)

    print(
        f"  Created composite feed ({feed_length * 1000:.0f}mm x "
        f"{feed_width * 1000:.0f}mm, {segments} segments)"
    )
    return feed


def create_feed_path_curve():
    """Create curve from spool exit to peel edge (feed path only).

    Returns:
        The curve object.
    """
    # Use waypoints 0-4 (spool_exit through peel_edge)
    feed_wps = WAYPOINTS[:5]

    curve_data = bpy.data.curves.new(name="FeedPathCurve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 64

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(feed_wps) - 1)

    for i, wp in enumerate(feed_wps):
        bp = spline.bezier_points[i]
        bp.co = Vector(wp["pos"])
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    curve_obj = bpy.data.objects.new("FeedPath", curve_data)
    bpy.context.scene.collection.objects.link(curve_obj)

    print(f"  Created feed path curve ({len(feed_wps)} points, spool→peel edge)")
    return curve_obj


def create_backing_return():
    """Create the backing paper strip that exits downward after peel edge.

    The backing paper wraps around the peel edge and exits below.

    Returns:
        The backing return mesh object.
    """
    backing_length = 0.080
    backing_width = LABEL_HEIGHT_M
    segments = 40

    # Build mesh without edit mode
    verts = []
    faces = []
    half_w = backing_width / 2
    for i in range(segments + 1):
        x = (i / segments) * backing_length
        verts.append((x, -half_w, 0))
        verts.append((x, half_w, 0))
    for i in range(segments):
        v0 = i * 2
        faces.append((v0, v0 + 2, v0 + 3, v0 + 1))

    mesh = bpy.data.meshes.new("BackingReturnMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    backing = bpy.data.objects.new("BackingReturn", mesh)
    bpy.context.scene.collection.objects.link(backing)

    # Create return path curve: peel edge → downward exit
    curve_data = bpy.data.curves.new(name="BackingReturnCurve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 32

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(1)

    bp0 = spline.bezier_points[0]
    bp0.co = PEEL_EDGE_POS
    bp0.handle_left_type = "AUTO"
    bp0.handle_right_type = "AUTO"

    exit_pos = Vector(
        (
            PEEL_EDGE_POS.x - 0.03,
            PEEL_EDGE_POS.y,
            PEEL_EDGE_POS.z - 0.06,
        )
    )
    bp1 = spline.bezier_points[1]
    bp1.co = exit_pos
    bp1.handle_left_type = "AUTO"
    bp1.handle_right_type = "AUTO"

    backing_curve = bpy.data.objects.new("BackingReturnPath", curve_data)
    bpy.context.scene.collection.objects.link(backing_curve)

    # Attach backing to its curve
    backing.location = PEEL_EDGE_POS
    mod = backing.modifiers.new("CurveDeform", "CURVE")
    mod.object = backing_curve
    mod.deform_axis = "POS_X"

    # White backing paper material
    mat = bpy.data.materials.new(name="Mat_BackingReturn")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.92, 0.90, 0.85, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
    backing.data.materials.append(mat)

    print("  Created backing return path (peel edge → downward exit)")
    return backing


def create_active_label():
    """Create the label that peels off and wraps around the vial.

    Uses shape keys: basis = flat on peel plate, key1 = wrapped around vial.
    Positions derived from VIAL_CENTER and PEEL_EDGE_POS constants.

    Returns:
        The active label mesh object.
    """
    label_w = LABEL_WIDTH_M  # 40mm — wraps around circumference
    label_h = LABEL_HEIGHT_M  # 20mm — along vial axis
    segments_x = 60  # around circumference
    segments_y = 4  # along vial axis

    # Build subdivided plane mesh without edit mode
    verts = []
    faces = []
    for iy in range(segments_y + 1):
        for ix in range(segments_x + 1):
            x = (ix / segments_x - 0.5) * label_w
            y = (iy / segments_y - 0.5) * label_h
            verts.append((x, y, 0))
    for iy in range(segments_y):
        for ix in range(segments_x):
            row = iy * (segments_x + 1)
            v0 = row + ix
            v1 = row + ix + 1
            v2 = row + ix + 1 + (segments_x + 1)
            v3 = row + ix + (segments_x + 1)
            faces.append((v0, v1, v2, v3))

    mesh_data = bpy.data.meshes.new("ActiveLabelMesh")
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()

    label = bpy.data.objects.new("ActiveLabel", mesh_data)
    bpy.context.scene.collection.objects.link(label)

    # Position flat on peel plate surface near peel edge
    # Label extends from peel edge toward the vial
    label.location = Vector(
        (
            PEEL_EDGE_POS.x - label_w / 2,  # centered between peel edge and vial
            PEEL_EDGE_POS.y,
            PEEL_EDGE_POS.z + 0.001,  # just above peel surface
        )
    )

    # --- Shape keys for wrapping ---
    label.shape_key_add(name="Basis", from_mix=False)
    sk_wrap = label.shape_key_add(name="Wrapped", from_mix=False)

    # Vial lies on side: cylinder axis is Y, wrapping in XZ plane
    vial_cx = VIAL_CENTER.x
    vial_cz = VIAL_CENTER.z
    wrap_r = VIAL_RADIUS_M + 0.0003  # tiny offset above surface

    for i, vert in enumerate(mesh_data.vertices):
        flat_x = vert.co.x
        flat_y = vert.co.y

        # Map X from [-label_w/2, label_w/2] to angle [0, 270°]
        t = (flat_x + label_w / 2) / label_w
        angle = t * math.radians(270)

        # Wrapped position: cylindrical coords around vial center
        wrapped_x = vial_cx + wrap_r * math.cos(angle) - label.location.x
        wrapped_y = flat_y  # Y stays the same (along vial axis)
        wrapped_z = vial_cz + wrap_r * math.sin(angle) - label.location.z

        sk_wrap.data[i].co = Vector((wrapped_x, wrapped_y, wrapped_z))

    sk_wrap.value = 0.0

    # Colored label material
    mat = bpy.data.materials.new(name="Mat_ActiveLabel")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.2, 0.6, 0.9, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.25
    label.data.materials.append(mat)

    print(f"  Created active label: flat at peel edge, wraps to "
          f"({vial_cx*1000:.0f}, {vial_cz*1000:.0f})mm")
    return label


def create_label_roll(spool_position):
    """Create a label roll on the spool.

    Returns:
        The label roll mesh object.
    """
    outer_r = SPOOL_FLANGE_DIAMETER_M / 2 * 0.9
    roll_height = LABEL_HEIGHT_M * 0.9

    roll_z = spool_position.z + roll_height / 2 + 0.003
    roll_loc = (spool_position.x, spool_position.y, roll_z)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=outer_r,
        depth=roll_height,
        location=roll_loc,
    )
    roll = bpy.context.active_object
    roll.name = "LabelRoll"
    for face in roll.data.polygons:
        face.use_smooth = True

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
        try:
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except AttributeError:
            pass


def setup_animation(fps, duration):
    """Set up all animation keyframes for the 4-act label application demo.

    Act 1 (0-20%):  Vial drops into cradle, material pre-loaded
    Act 2 (20-60%): Composite feed advances, label separates at peel edge
    Act 3 (60-90%): Label wraps around spinning vial
    Act 4 (90-100%): Hold — show completed labeled vial

    Args:
        fps: Frames per second.
        duration: Total duration in seconds.
    """
    total = int(fps * duration)

    # Act boundaries
    act1_end = int(total * 0.20)
    act2_end = int(total * 0.60)
    act3_end = int(total * 0.90)

    # --- Act 1: Vial drop-in ---
    vial = bpy.data.objects.get("Vial")
    if vial:
        final_z = vial.get("final_z", VIAL_CENTER.z)

        # Start above
        vial.keyframe_insert(data_path="location", frame=1)
        # Land in cradle
        vial.location.z = final_z
        vial.keyframe_insert(data_path="location", frame=act1_end)
        # Hold position through rest of animation
        vial.keyframe_insert(data_path="location", frame=total)
        print(f"  Vial: drop-in frames 1-{act1_end}")

    # --- Act 2: Composite feed advances ---
    feed = bpy.data.objects.get("CompositeFeed")
    if feed:
        # Start pulled back (hidden behind spool area)
        feed.location.x = WAYPOINTS[0]["pos"][0] - 0.35
        feed.keyframe_insert(data_path="location", frame=1)
        feed.keyframe_insert(data_path="location", frame=act1_end)

        # Advance through feed path — strip slides to show material feeding
        feed.location.x = WAYPOINTS[0]["pos"][0]
        feed.keyframe_insert(data_path="location", frame=act2_end)

        # Hold
        feed.keyframe_insert(data_path="location", frame=total)
        set_linear_interpolation(feed)
        print(f"  Composite feed: advance frames {act1_end}-{act2_end}")

    # --- Act 2: Backing return appears ---
    backing = bpy.data.objects.get("BackingReturn")
    if backing:
        # Hidden at start (scale to 0)
        backing.scale = (0.0, 1.0, 1.0)
        backing.keyframe_insert(data_path="scale", frame=1)
        backing.keyframe_insert(
            data_path="scale", frame=int(act1_end + (act2_end - act1_end) * 0.3)
        )

        # Grows as backing feeds through
        backing.scale = (1.0, 1.0, 1.0)
        backing.keyframe_insert(data_path="scale", frame=act2_end)
        backing.keyframe_insert(data_path="scale", frame=total)
        print("  Backing return: appear during Act 2")

    # --- Act 2-3: Active label shape key (flat → wrapped) ---
    label = bpy.data.objects.get("ActiveLabel")
    if label and label.data.shape_keys:
        wrap_key = label.data.shape_keys.key_blocks.get("Wrapped")
        if wrap_key:
            # Hidden during Act 1 (scale 0)
            label.scale = (0.0, 0.0, 0.0)
            label.keyframe_insert(data_path="scale", frame=1)
            label.keyframe_insert(data_path="scale", frame=int(act2_end * 0.7))

            # Appear at peel edge when composite reaches it
            label.scale = (1.0, 1.0, 1.0)
            label.keyframe_insert(data_path="scale", frame=int(act2_end * 0.8))

            # Start flat (on peel plate)
            wrap_key.value = 0.0
            wrap_key.keyframe_insert(data_path="value", frame=int(act2_end * 0.8))
            wrap_key.keyframe_insert(data_path="value", frame=act2_end)

            # Wrap around vial during Act 3
            wrap_key.value = 1.0
            wrap_key.keyframe_insert(data_path="value", frame=act3_end)
            wrap_key.keyframe_insert(data_path="value", frame=total)

            print(
                f"  Active label: appear at {int(act2_end * 0.8)}, wrap {act2_end}-{act3_end}"
            )

    # --- Act 3: Vial rotation ---
    if vial:
        # Vial lies on side with rotation_euler.x = 90°, so spin around Y
        vial.rotation_euler = (math.radians(90), 0, 0)
        vial.keyframe_insert(data_path="rotation_euler", frame=act2_end)

        # Rotate around Y axis (vial's length axis when lying on side)
        vial.rotation_euler = (math.radians(90), math.radians(300), 0)
        vial.keyframe_insert(data_path="rotation_euler", frame=act3_end)

        # Hold
        vial.keyframe_insert(data_path="rotation_euler", frame=total)
        set_linear_interpolation(vial)
        print(f"  Vial: rotate frames {act2_end}-{act3_end}")

    # --- Label roll shrinking (Acts 2-3) ---
    roll = bpy.data.objects.get("LabelRoll")
    if roll:
        roll.scale = (1.0, 1.0, 1.0)
        roll.keyframe_insert(data_path="scale", frame=1)
        roll.keyframe_insert(data_path="scale", frame=act1_end)
        roll.scale = (0.7, 0.7, 1.0)
        roll.keyframe_insert(data_path="scale", frame=act3_end)
        roll.keyframe_insert(data_path="scale", frame=total)
        print(f"  Label roll: shrink frames {act1_end}-{act3_end}")

    # --- Dancer arm oscillation (Acts 2-3) ---
    dancer = bpy.data.objects.get("DancerArm")
    if dancer:
        osc_count = 10
        for i in range(osc_count + 1):
            frame = act1_end + int((act3_end - act1_end) * i / osc_count)
            angle = math.radians(5.0 * math.sin(i * math.pi * 2 / osc_count))
            dancer.rotation_euler.z = angle
            dancer.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
        print(f"  Dancer arm: oscillate frames {act1_end}-{act3_end}")

    print(f"  Animation: {total} frames ({duration}s @ {fps}fps)")
    print(
        f"  Acts: setup 1-{act1_end}, feed {act1_end}-{act2_end}, "
        f"wrap {act2_end}-{act3_end}, hold {act3_end}-{total}"
    )


def setup_camera_animation(center, dist, fps, duration):
    """Animate camera as a gentle orbit — no aggressive close-ups.

    Keeps the full machine visible throughout with a slow orbit that
    shifts attention toward the peel/vial area during Acts 2-3.
    Camera stays at a comfortable distance to avoid blur/noise.
    """
    total = int(fps * duration)
    cam = bpy.data.objects.get("AnimCam")
    if not cam:
        return

    act1_end = int(total * 0.20)
    act2_end = int(total * 0.60)
    act3_end = int(total * 0.90)

    # Fixed orbit radius — never closer than 0.25m
    orbit_r = max(dist * 0.7, 0.25)
    orbit_h = max(dist * 0.4, 0.12)

    # Midpoint between peel edge and vial — the action zone
    action_center = (PEEL_EDGE_POS + VIAL_CENTER) / 2

    # Act 1: Wide 3/4 view from front-right
    angle1 = math.radians(-40)
    cam.location = Vector((
        center.x + orbit_r * math.cos(angle1),
        center.y + orbit_r * math.sin(angle1),
        center.z + orbit_h,
    ))
    look_at(cam, center)
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_euler", frame=1)

    # Act 1 end: slight orbit
    angle2 = math.radians(-30)
    cam.location = Vector((
        center.x + orbit_r * math.cos(angle2),
        center.y + orbit_r * math.sin(angle2),
        center.z + orbit_h * 0.9,
    ))
    look_at(cam, center)
    cam.keyframe_insert(data_path="location", frame=act1_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=act1_end)

    # Act 2: Orbit toward action area, look at peel/vial zone
    angle3 = math.radians(-20)
    cam.location = Vector((
        action_center.x + orbit_r * 0.8 * math.cos(angle3),
        action_center.y + orbit_r * 0.8 * math.sin(angle3),
        action_center.z + orbit_h * 0.8,
    ))
    look_at(cam, action_center)
    cam.keyframe_insert(data_path="location", frame=act2_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=act2_end)

    # Act 3: Slightly closer, focused on wrapping
    angle4 = math.radians(-15)
    cam.location = Vector((
        action_center.x + orbit_r * 0.7 * math.cos(angle4),
        action_center.y + orbit_r * 0.7 * math.sin(angle4),
        action_center.z + orbit_h * 0.7,
    ))
    look_at(cam, VIAL_CENTER)
    cam.keyframe_insert(data_path="location", frame=act3_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=act3_end)

    # Act 4: Pull back to show result
    angle5 = math.radians(-35)
    cam.location = Vector((
        center.x + orbit_r * math.cos(angle5),
        center.y + orbit_r * math.sin(angle5),
        center.z + orbit_h,
    ))
    look_at(cam, VIAL_CENTER)
    cam.keyframe_insert(data_path="location", frame=total)
    cam.keyframe_insert(data_path="rotation_euler", frame=total)

    # No DoF — keep everything sharp
    cam.data.dof.use_dof = False

    print(f"  Camera: gentle orbit, min distance {orbit_r*1000:.0f}mm")


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
    scene.render.film_transparent = False

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
    print("Shows: vial placement → label feed → separation → wrapping")

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

    # Get component positions
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    positions = {e["name"]: Vector(e["position"]) * 0.001 for e in manifest}

    # Create animation objects (positions from derived constants)
    print("\n2. Creating animation objects...")
    create_vial()
    feed = create_composite_feed()
    create_backing_return()
    create_active_label()
    create_label_roll(positions["SpoolHolder"])

    # Create feed path curve and attach composite feed
    print("\n3. Creating feed path curve...")
    feed_curve = create_feed_path_curve()
    feed.location = Vector(WAYPOINTS[0]["pos"])
    mod = feed.modifiers.new("CurveDeform", "CURVE")
    mod.object = feed_curve
    mod.deform_axis = "POS_X"
    print("  Attached composite feed to path curve")

    # Scene setup
    print("\n4. Setting up scene...")
    setup_ground_plane(center, bbox_min)
    setup_three_point_lighting(center)

    # Camera — initial establishing shot
    dist = compute_camera_distance(bbox_min, bbox_max)
    cam_pos = (
        center.x + dist * 0.6,
        center.y - dist * 0.7,
        center.z + dist * 0.4,
    )
    setup_camera(cam_pos, tuple(center), lens=50, dof_enabled=False)

    # Configure render
    print("\n5. Configuring render...")
    configure_render(
        args.resolution, args.samples, args.fps, args.duration, args.preview
    )

    # Animation keyframes — the core storytelling
    print("\n6. Setting up animation (4-act structure)...")
    setup_animation(args.fps, args.duration)

    # Camera animation
    print("\n7. Setting up camera animation...")
    setup_camera_animation(center, dist, args.fps, args.duration)

    scene = bpy.context.scene
    scene.render.use_motion_blur = False

    # Render
    total_frames = scene.frame_end
    scene.render.filepath = os.path.join(args.output, "frame_")

    print(f"\n8. Rendering {total_frames} frames...")
    bpy.ops.render.render(animation=True)

    print(f"\nAnimation render complete — {total_frames} frames saved to {args.output}")


if __name__ == "__main__":
    main()
