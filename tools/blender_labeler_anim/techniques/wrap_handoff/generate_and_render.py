"""Technique A: Two-geometry handoff wrap.

Keeps a flat label strip near the peel edge and a wrapped cylindrical patch
on the vial surface. As vial_rot_deg increases, the wrapped patch is revealed
and the flat strip is hidden — creating a deterministic "engineering viz" wrap.

Usage:
    blender -b -P generate_and_render.py -- --out ./output --frames 1 120 --fps 24
"""
import sys
import math
from pathlib import Path

import bpy
from mathutils import Vector

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from core import constants as C
from core.generate_scene import build_base_scene
from core.render import setup_render, setup_output, render_animation, encode_mp4, set_linear_interpolation
from core.cli import parse_args
from core.materials import create_label_material, create_backing_material
from core.geom_nodes_lib import (
    new_node_group, get_group_io_nodes, apply_gn_modifier,
)


# ---------------------------------------------------------------------------
# Flat label strip (near peel edge)
# ---------------------------------------------------------------------------

def create_flat_label_strip():
    """Create a planar label strip positioned near the peel edge.

    The strip lies in the XZ plane, extending from the peel edge toward
    where it would contact the vial.
    """
    pe = C.PEEL_EDGE
    vc = C.VIAL_CENTER
    w = C.LABEL_HEIGHT  # along Y (vial axis)
    h = C.LABEL_WIDTH  # along X (feed direction) — will be trimmed

    # Build a subdivided plane for smooth trimming
    verts = []
    faces = []
    segs_u = 60  # along feed direction
    segs_v = 4  # across width

    # Strip from peel edge toward vial contact
    contact_x = vc[0] - C.VIAL_RADIUS
    start_x = pe[0]
    start_z = pe[2]
    end_x = contact_x
    end_z = vc[2]

    for i in range(segs_u + 1):
        u = i / segs_u
        x = start_x + u * (end_x - start_x)
        z = start_z + u * (end_z - start_z) + 2 * math.sin(u * math.pi)  # slight arc
        for j in range(segs_v + 1):
            v = j / segs_v - 0.5
            y = pe[1] + v * w
            verts.append((x, y, z + C.LABEL_THICKNESS))

    for i in range(segs_u):
        for j in range(segs_v):
            a = i * (segs_v + 1) + j
            b = a + 1
            c = a + (segs_v + 1) + 1
            d = a + (segs_v + 1)
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new('FlatLabelMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new('FlatLabel', mesh)
    bpy.context.scene.collection.objects.link(obj)

    mat = create_label_material('FlatLabelMat', (0.95, 0.92, 0.85, 1.0))
    obj.data.materials.append(mat)

    return obj


# ---------------------------------------------------------------------------
# Wrapped label patch (on vial surface)
# ---------------------------------------------------------------------------

def create_wrapped_label_patch():
    """Create a cylindrical label patch conforming to the vial surface.

    The patch wraps up to 270° around the vial, offset slightly above
    the surface to avoid z-fighting.
    """
    vc = C.VIAL_CENTER
    r = C.VIAL_RADIUS + 0.3  # offset above surface
    wrap_max = math.radians(C.LABEL_WRAP_ANGLE)
    w = C.LABEL_HEIGHT  # along vial axis (Y)

    segs_u = 80  # around circumference
    segs_v = 4  # along vial axis

    verts = []
    faces = []

    # Start angle: where label first contacts vial (from -X side)
    # Label approaches from the left, so contact is at angle π (180°)
    start_angle = math.pi

    for i in range(segs_u + 1):
        u = i / segs_u
        angle = start_angle - u * wrap_max  # wrap CW when viewed from +Y
        x = vc[0] + r * math.cos(angle)
        z = vc[2] + r * math.sin(angle)
        for j in range(segs_v + 1):
            v = j / segs_v - 0.5
            y = vc[1] + v * w
            verts.append((x, y, z))

    for i in range(segs_u):
        for j in range(segs_v):
            a = i * (segs_v + 1) + j
            b = a + 1
            c = a + (segs_v + 1) + 1
            d = a + (segs_v + 1)
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new('WrappedLabelMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # Compute smooth normals
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new('WrappedLabel', mesh)
    bpy.context.scene.collection.objects.link(obj)

    mat = create_label_material('WrappedLabelMat', (0.95, 0.92, 0.85, 1.0))
    obj.data.materials.append(mat)

    return obj


# ---------------------------------------------------------------------------
# GN mask: reveal/hide based on CTRL.vial_rot_deg
# ---------------------------------------------------------------------------

def create_handoff_reveal_group(name, mode='reveal'):
    """Create a GN group that masks geometry based on a position attribute.

    For 'reveal' mode: reveals geometry progressively (for wrapped patch).
    For 'hide' mode: hides geometry progressively (for flat strip).

    Uses the vertex index ratio as a proxy for along-strip position.

    Inputs:
        Geometry
        Factor (0-1): how much to reveal/hide
    Output:
        Geometry (masked)
    """
    tree = new_node_group(
        name,
        inputs=[
            ('Geometry', 'Geometry'),
            ('Factor', 'Float', 0.0),
        ],
        outputs=[('Geometry', 'Geometry')]
    )

    nodes = tree.nodes
    links = tree.links
    group_in, group_out = get_group_io_nodes(tree)
    group_in.location = (-600, 0)
    group_out.location = (600, 0)

    # Get vertex index
    idx = nodes.new('GeometryNodeInputIndex')
    idx.location = (-400, -100)

    # Domain size to get total verts
    dom = nodes.new('GeometryNodeAttributeDomainSize')
    dom.location = (-400, -250)
    links.new(group_in.outputs['Geometry'], dom.inputs['Geometry'])

    # Normalize index: index / total
    divide = nodes.new('ShaderNodeMath')
    divide.operation = 'DIVIDE'
    divide.location = (-200, -150)
    links.new(idx.outputs['Index'], divide.inputs[0])
    links.new(dom.outputs['Point Count'], divide.inputs[1])

    # Compare with Factor
    compare = nodes.new('FunctionNodeCompare')
    compare.data_type = 'FLOAT'
    compare.location = (0, -100)

    if mode == 'reveal':
        # Keep vertices where normalized_index < factor
        compare.operation = 'LESS_THAN'
        links.new(divide.outputs['Value'], compare.inputs['A'])
        links.new(group_in.outputs['Factor'], compare.inputs['B'])
    else:
        # Keep vertices where normalized_index > factor
        compare.operation = 'GREATER_THAN'
        links.new(divide.outputs['Value'], compare.inputs['A'])
        links.new(group_in.outputs['Factor'], compare.inputs['B'])

    # Delete geometry where condition is false
    delete = nodes.new('GeometryNodeDeleteGeometry')
    delete.location = (200, 0)
    delete.domain = 'FACE'
    # Invert: delete where NOT our condition
    bool_not = nodes.new('FunctionNodeBooleanMath')
    bool_not.operation = 'NOT'
    bool_not.location = (100, -100)
    links.new(compare.outputs['Result'], bool_not.inputs[0])

    links.new(group_in.outputs['Geometry'], delete.inputs['Geometry'])
    links.new(bool_not.outputs['Boolean'], delete.inputs['Selection'])
    links.new(delete.outputs['Geometry'], group_out.inputs['Geometry'])

    return tree


def setup_handoff_drivers(flat_obj, wrapped_obj, ctrl_obj):
    """Set up drivers so CTRL.vial_rot_deg controls the handoff.

    vial_rot_deg [0..270] maps to factor [0..1]:
    - Wrapped patch: factor = vial_rot_deg / 270 (reveal)
    - Flat strip: factor = vial_rot_deg / 270 (hide)
    """
    max_deg = C.LABEL_WRAP_ANGLE

    # Wrapped: reveal GN
    reveal_group = create_handoff_reveal_group('WrappedReveal', 'reveal')
    reveal_mod = apply_gn_modifier(wrapped_obj, reveal_group, 'WrappedReveal')

    # Flat: hide GN
    hide_group = create_handoff_reveal_group('FlatHide', 'hide')
    hide_mod = apply_gn_modifier(flat_obj, hide_group, 'FlatHide')

    # Add drivers for Factor
    for mod in [reveal_mod, hide_mod]:
        for key in mod.keys():
            if 'Factor' in key or 'factor' in key:
                try:
                    fc = mod.driver_add(f'["{key}"]')
                    d = fc.driver
                    d.type = 'SCRIPTED'
                    v = d.variables.new()
                    v.name = 'rot'
                    v.type = 'SINGLE_PROP'
                    t = v.targets[0]
                    t.id = ctrl_obj
                    t.data_path = '["vial_rot_deg"]'
                    d.expression = f'min(rot / {max_deg}, 1.0)'
                except Exception as e:
                    print(f"Driver error: {e}")


# ---------------------------------------------------------------------------
# Vial rotation driver
# ---------------------------------------------------------------------------

def setup_vial_rotation_driver(vial_obj, ctrl_obj):
    """Drive vial Y rotation from CTRL.vial_rot_deg.

    Vial has rotation_euler.x = 90° (lying on side), so rotation around
    its length axis is rotation_euler.y in local space.
    """
    fc = vial_obj.driver_add('rotation_euler', 1)  # Y component
    d = fc.driver
    d.type = 'SCRIPTED'
    v = d.variables.new()
    v.name = 'deg'
    v.type = 'SINGLE_PROP'
    t = v.targets[0]
    t.id = ctrl_obj
    t.data_path = '["vial_rot_deg"]'
    d.expression = 'radians(deg)'


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def keyframe_ctrl(ctrl_obj, frame_start, frame_end):
    """Keyframe CTRL for handoff demo."""
    total = frame_end - frame_start

    # Ramp vial_rot_deg 0 → 270 over full duration
    ctrl_obj['vial_rot_deg'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=frame_start)
    ctrl_obj['vial_rot_deg'] = 270.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=frame_end)

    # feed_mm ramps along with rotation
    ctrl_obj['feed_mm'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=frame_start)
    ctrl_obj['feed_mm'] = 120.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=frame_end)

    # Dancer oscillation
    for i in range(5):
        f = frame_start + int(i * total / 4)
        ctrl_obj['dancer_deg'] = 10.0 * (1 if i % 2 == 0 else -1)
        ctrl_obj.keyframe_insert(data_path='["dancer_deg"]', frame=f)

    # Linear interpolation
    set_linear_interpolation(ctrl_obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    objects = build_base_scene()
    ctrl = objects['ctrl']
    vial = objects['vial']

    # Create handoff geometries
    flat_label = create_flat_label_strip()
    wrapped_label = create_wrapped_label_patch()

    # Setup drivers
    setup_handoff_drivers(flat_label, wrapped_label, ctrl)
    setup_vial_rotation_driver(vial, ctrl)

    # Keyframe
    frame_start, frame_end = args.frames
    keyframe_ctrl(ctrl, frame_start, frame_end)

    # Render
    setup_render(
        engine=args.engine,
        samples=args.samples,
        resolution=tuple(args.resolution),
        fps=args.fps,
        frame_range=tuple(args.frames),
    )
    out_dir = setup_output(output_dir=args.out)

    print(f"Rendering handoff wrap: frames {frame_start}–{frame_end} to {out_dir}")
    render_animation()

    if args.encode_mp4:
        mp4 = encode_mp4(str(out_dir), fps=args.fps)
        if mp4:
            print(f"MP4: {mp4}")

    print("Done.")


if __name__ == '__main__':
    main()
