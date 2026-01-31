"""Curve-driven label routing with peel separation.

Generates the label/backing path as Blender curves, creates ribbon meshes
via Geometry Nodes, and animates feed via CTRL.feed_mm trim/reveal.

Usage:
    blender -b -P generate_and_render.py -- --out ./output --frames 1 120 --fps 24
"""
import sys
import math
from pathlib import Path

import bpy

# Add parent dirs to path for core imports
_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from core import constants as C
from core.generate_scene import build_base_scene
from core.render import setup_render, setup_output, render_animation, encode_mp4, set_linear_interpolation
from core.cli import parse_args
from core.materials import create_label_material, create_backing_material
from core.geom_nodes_lib import (
    new_node_group, get_group_io_nodes, apply_gn_modifier,
    create_curve_to_ribbon_group, create_trim_reveal_group,
)


# ---------------------------------------------------------------------------
# Curve construction helpers
# ---------------------------------------------------------------------------

def _vec(t):
    """Convert a tuple to a Blender Vector-compatible form."""
    return t


def arc_points(center, radius, start_angle, end_angle, segments=12):
    """Generate points along a circular arc in the XZ plane.

    Angles are in radians, measured CCW from +X axis.
    Y is kept constant from *center*.
    """
    pts = []
    for i in range(segments + 1):
        t = i / segments
        angle = start_angle + t * (end_angle - start_angle)
        x = center[0] + radius * math.cos(angle)
        z = center[2] + radius * math.sin(angle)
        pts.append((x, center[1], z))
    return pts


def compute_tangent_angle(from_pt, to_center, radius):
    """Compute the tangent angle on a circle from an external point (XZ plane)."""
    dx = to_center[0] - from_pt[0]
    dz = to_center[2] - from_pt[2]
    dist = math.sqrt(dx * dx + dz * dz)
    if dist <= radius:
        return math.atan2(dz, dx)
    tangent_offset = math.acos(radius / dist)
    base_angle = math.atan2(dz, dx)
    return base_angle - tangent_offset


# ---------------------------------------------------------------------------
# Label path curve (spool → dancer → guide → peel edge)
# ---------------------------------------------------------------------------

def build_label_path_points():
    """Compute the full label path waypoints including roller wrap arcs."""
    pts = []

    # Start: spool exit
    pts.append(C.SPOOL_EXIT)

    # Approach dancer roller — tangent entry
    # Simplified: straight segment to arc start, then arc, then exit
    dancer_c = C.DANCER_ROLLER_CENTER
    dancer_r = C.DANCER_ROLLER_RADIUS

    # Arc around dancer (wrap ~180° on top)
    d_start_angle = math.radians(180)  # coming from left
    d_end_angle = math.radians(0)  # exiting right
    dancer_arc = arc_points(dancer_c, dancer_r, d_start_angle, d_end_angle, 16)
    pts.extend(dancer_arc)

    # Approach guide roller
    guide_c = C.GUIDE_ROLLER_CENTER
    guide_r = C.GUIDE_ROLLER_RADIUS

    # Arc around guide roller (wrap ~180° on bottom)
    g_start_angle = math.radians(180)
    g_end_angle = math.radians(0)
    guide_arc = arc_points(guide_c, guide_r, g_start_angle, g_end_angle, 16)
    pts.extend(guide_arc)

    # Straight to peel entry, then peel edge
    pts.append(C.PEEL_ENTRY)
    pts.append(C.PEEL_EDGE)

    return pts


def build_backing_exit_points():
    """Compute backing paper path after peel separation.

    Wraps ~160° around peel radius then exits downward.
    """
    pe = C.PEEL_EDGE
    pr = C.PEEL_RADIUS
    wrap_rad = math.radians(C.BACKING_WRAP_ANGLE)

    # Start at peel edge, arc downward
    start_angle = math.radians(90)  # top of peel radius
    end_angle = start_angle - wrap_rad  # wrapping CW (downward)

    arc = arc_points(
        (pe[0], pe[1], pe[2] - pr),  # center of peel radius circle
        pr, start_angle, end_angle, 12
    )

    # Continue downward exit
    last = arc[-1]
    arc.append((last[0] + 5, last[1], last[2] - 20))

    return arc


def build_label_exit_points():
    """Compute label path from peel edge toward vial contact."""
    pe = C.PEEL_EDGE
    vc = C.VIAL_CENTER

    # Contact point on vial (closest point on vial surface facing peel)
    contact_x = vc[0] - C.VIAL_RADIUS  # left side of vial
    contact = (contact_x, vc[1], vc[2])

    # Short bridge from peel edge to vial contact
    mid = (
        (pe[0] + contact[0]) / 2,
        (pe[1] + contact[1]) / 2,
        (pe[2] + contact[2]) / 2 + 2,  # slight lift
    )

    return [pe, mid, contact]


# ---------------------------------------------------------------------------
# Blender curve creation
# ---------------------------------------------------------------------------

def create_poly_curve(name, points, closed=False):
    """Create a Blender curve object from a list of 3D points."""
    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12

    spline = curve_data.splines.new('POLY')
    spline.points.add(len(points) - 1)  # first point already exists

    for i, pt in enumerate(points):
        spline.points[i].co = (pt[0], pt[1], pt[2], 1.0)

    spline.use_cyclic_u = closed

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Geometry Nodes ribbon + trim setup
# ---------------------------------------------------------------------------

def setup_ribbon_with_trim(curve_obj, width, thickness, material, name_prefix):
    """Apply CurveToRibbon + TrimReveal GN modifiers and material."""
    # First: trim/reveal
    trim_group = create_trim_reveal_group(f'{name_prefix}_Trim')
    trim_mod = apply_gn_modifier(curve_obj, trim_group, f'{name_prefix}_Trim')

    # Create a mesh object from the curve for the ribbon
    ribbon_curve = curve_obj.copy()
    ribbon_curve.data = curve_obj.data.copy()
    ribbon_curve.name = f'{name_prefix}_Ribbon'
    bpy.context.scene.collection.objects.link(ribbon_curve)

    ribbon_group = create_curve_to_ribbon_group(f'{name_prefix}_Ribbon')
    ribbon_mod = apply_gn_modifier(ribbon_curve, ribbon_group, f'{name_prefix}_Ribbon')

    # Set width/thickness via modifier inputs
    # In Blender 5.0, modifier inputs are accessed via the modifier's keys
    for key in ribbon_mod.keys():
        if 'Width' in key or 'width' in key:
            ribbon_mod[key] = width
        if 'Thickness' in key or 'thickness' in key:
            ribbon_mod[key] = thickness

    # Apply material
    if not ribbon_curve.data.materials:
        ribbon_curve.data.materials.append(material)
    else:
        ribbon_curve.data.materials[0] = material

    return curve_obj, ribbon_curve


def add_feed_driver(modifier, ctrl_obj, prop_name='feed_mm', max_feed=150.0):
    """Add a driver to a GN modifier's Factor input driven by CTRL.feed_mm.

    Maps feed_mm [0..max_feed] → factor [0..1].
    """
    # Find the Factor input identifier
    for key in modifier.keys():
        if 'Factor' in key or 'factor' in key:
            try:
                fcurve = modifier.driver_add(f'["{key}"]')
                driver = fcurve.driver
                driver.type = 'SCRIPTED'

                var = driver.variables.new()
                var.name = 'feed'
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id = ctrl_obj
                target.data_path = f'["{prop_name}"]'

                driver.expression = f'min(feed / {max_feed}, 1.0)'
                return True
            except Exception as e:
                print(f"Driver setup failed: {e}")
    return False


# ---------------------------------------------------------------------------
# Dancer arm (simple kinematic linkage)
# ---------------------------------------------------------------------------

def create_dancer_arm(ctrl_obj):
    """Create a simple dancer arm driven by CTRL.dancer_deg."""
    pivot = C.DANCER_PIVOT
    roller_c = C.DANCER_ROLLER_CENTER
    arm_length = math.sqrt(
        (roller_c[0] - pivot[0]) ** 2
        + (roller_c[1] - pivot[1]) ** 2
        + (roller_c[2] - pivot[2]) ** 2
    )

    # Create arm as a thin cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=2, depth=arm_length,
        location=(
            (pivot[0] + roller_c[0]) / 2,
            (pivot[1] + roller_c[1]) / 2,
            (pivot[2] + roller_c[2]) / 2,
        ),
        vertices=8,
    )
    arm = bpy.context.active_object
    arm.name = 'DancerArm'

    # Orient arm from pivot to roller
    dx = roller_c[0] - pivot[0]
    dy = roller_c[1] - pivot[1]
    dz = roller_c[2] - pivot[2]
    # Compute rotation to align cylinder with arm direction
    horiz = math.sqrt(dx * dx + dy * dy)
    pitch = math.atan2(dz, horiz)
    yaw = math.atan2(dy, dx)
    arm.rotation_euler = (math.radians(90) - pitch, 0, yaw)

    # Set pivot as origin for rotation
    arm.location = pivot
    # We'll use the object's origin at pivot and offset geometry
    # For simplicity, just parent to an empty at pivot
    bpy.ops.object.empty_add(type='SINGLE_ARROW', location=pivot)
    pivot_empty = bpy.context.active_object
    pivot_empty.name = 'DancerPivot'

    arm.parent = pivot_empty

    # Driver: rotate pivot_empty.Z from CTRL.dancer_deg
    fcurve = pivot_empty.driver_add('rotation_euler', 2)  # Z rotation
    driver = fcurve.driver
    driver.type = 'SCRIPTED'
    var = driver.variables.new()
    var.name = 'deg'
    var.type = 'SINGLE_PROP'
    target = var.targets[0]
    target.id = ctrl_obj
    target.data_path = '["dancer_deg"]'
    driver.expression = 'radians(deg)'

    return arm, pivot_empty


# ---------------------------------------------------------------------------
# Animation: keyframe CTRL properties
# ---------------------------------------------------------------------------

def keyframe_ctrl(ctrl_obj, frame_start, frame_end):
    """Keyframe CTRL properties for a demo animation.

    Timeline:
    - Frames start..33%: Feed label (feed_mm 0→100), dancer oscillates
    - Frames 33%..100%: Continue feed + vial rotation (vial_rot_deg 0→270)
    """
    total = frame_end - frame_start
    feed_end = frame_start + total  # feed runs entire duration
    vial_start = frame_start + total // 3
    vial_end = frame_end

    # feed_mm: 0 → 120
    ctrl_obj['feed_mm'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=frame_start)
    ctrl_obj['feed_mm'] = 120.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=feed_end)

    # vial_rot_deg: 0 → 270 (starts at 1/3)
    ctrl_obj['vial_rot_deg'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=vial_start)
    ctrl_obj['vial_rot_deg'] = 270.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=vial_end)

    # dancer_deg: gentle oscillation
    for i in range(5):
        f = frame_start + int(i * total / 4)
        ctrl_obj['dancer_deg'] = 15.0 * (1 if i % 2 == 0 else -1)
        ctrl_obj.keyframe_insert(data_path='["dancer_deg"]', frame=f)

    # Set interpolation to linear for feed/vial
    set_linear_interpolation(ctrl_obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Build base scene
    objects = build_base_scene()
    ctrl = objects['ctrl']

    # Build curves
    label_path_pts = build_label_path_points()
    backing_pts = build_backing_exit_points()
    label_exit_pts = build_label_exit_points()

    label_curve = create_poly_curve('LabelPath', label_path_pts)
    backing_curve = create_poly_curve('BackingPath', backing_pts)
    label_exit_curve = create_poly_curve('LabelExit', label_exit_pts)

    # Materials
    label_mat = create_label_material()
    backing_mat = create_backing_material()

    # Ribbon meshes with GN
    label_path_obj, label_ribbon = setup_ribbon_with_trim(
        label_curve, C.LABEL_HEIGHT, C.LABEL_THICKNESS, label_mat, 'Label'
    )
    backing_path_obj, backing_ribbon = setup_ribbon_with_trim(
        backing_curve, C.LABEL_HEIGHT, C.LABEL_THICKNESS * 0.8, backing_mat, 'Backing'
    )
    label_exit_obj, label_exit_ribbon = setup_ribbon_with_trim(
        label_exit_curve, C.LABEL_HEIGHT, C.LABEL_THICKNESS, label_mat, 'LabelExit'
    )

    # Add feed drivers to trim modifiers
    for obj in [label_path_obj, backing_path_obj, label_exit_obj]:
        for mod in obj.modifiers:
            if 'Trim' in mod.name:
                add_feed_driver(mod, ctrl)

    # Dancer arm
    create_dancer_arm(ctrl)

    # Keyframe animation
    frame_start, frame_end = args.frames
    keyframe_ctrl(ctrl, frame_start, frame_end)

    # Render setup
    setup_render(
        engine=args.engine,
        samples=args.samples,
        resolution=tuple(args.resolution),
        fps=args.fps,
        frame_range=tuple(args.frames),
    )
    out_dir = setup_output(output_dir=args.out)

    print(f"Rendering frames {frame_start}–{frame_end} to {out_dir}")
    render_animation()

    if args.encode_mp4:
        mp4 = encode_mp4(str(out_dir), fps=args.fps)
        if mp4:
            print(f"MP4 encoded: {mp4}")

    print("Done.")


if __name__ == '__main__':
    main()
