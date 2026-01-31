"""Technique B: Pure Geometry Nodes polar wrap.

Performs a flat-to-cylindrical coordinate deformation entirely within
Geometry Nodes, mapping distance along the label strip into an angle
around the vial circumference.

Usage:
    blender -b -P generate_and_render.py -- --out ./output --frames 1 120 --fps 24
"""
import sys
import math
from pathlib import Path

import bpy

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from core import constants as C
from core.generate_scene import build_base_scene
from core.render import setup_render, setup_output, render_animation, encode_mp4, set_linear_interpolation
from core.cli import parse_args
from core.materials import create_label_material
from core.geom_nodes_lib import new_node_group, get_group_io_nodes, apply_gn_modifier


# ---------------------------------------------------------------------------
# Flat label mesh (source for deformation)
# ---------------------------------------------------------------------------

def create_flat_label_mesh():
    """Create a flat label ribbon positioned at the peel edge.

    The strip extends along +X (wrap direction) and +Y (vial axis direction).
    It will be deformed by the GN polar wrap into cylindrical coordinates.
    """
    pe = C.PEEL_EDGE
    # Label dimensions
    # wrap_length = circumference fraction: 2*pi*r * (270/360)
    wrap_length = 2 * math.pi * C.VIAL_RADIUS * (C.LABEL_WRAP_ANGLE / 360.0)
    w = C.LABEL_HEIGHT  # along Y

    segs_u = 100  # along wrap direction
    segs_v = 6  # across width (Y)

    verts = []
    faces = []

    for i in range(segs_u + 1):
        u = i / segs_u
        x = u * wrap_length  # local X = distance along wrap
        for j in range(segs_v + 1):
            v = j / segs_v - 0.5
            y = v * w
            verts.append((x, y, 0))

    for i in range(segs_u):
        for j in range(segs_v):
            a = i * (segs_v + 1) + j
            b = a + 1
            c = a + (segs_v + 1) + 1
            d = a + (segs_v + 1)
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new('PolarLabelMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new('PolarLabel', mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Position at peel edge initially
    obj.location = (pe[0], pe[1], pe[2])

    mat = create_label_material('PolarLabelMat', (0.95, 0.92, 0.85, 1.0))
    obj.data.materials.append(mat)

    return obj, wrap_length


# ---------------------------------------------------------------------------
# Geometry Nodes: Polar wrap deformation
# ---------------------------------------------------------------------------

def create_polar_wrap_gn_group(wrap_length):
    """Create a GN group that deforms flat geometry into cylindrical wrap.

    Maps vertex X position [0..wrap_length] → angle [0..wrap_max_angle]:
        angle = (x / wrap_length) * wrap_max_angle * wrap_factor
        new_x = vial_cx + (r + eps) * cos(start_angle - angle)
        new_z = vial_cz + (r + eps) * sin(start_angle - angle)
        new_y = vial_cy + original_y

    A smooth transition zone blends between flat and wrapped states
    based on distance from the wrap start.

    Inputs:
        Geometry
        Wrap Factor (0-1): driven by CTRL.vial_rot_deg / 270
        Blend Zone (float): size of transition zone in mm
    Output:
        Geometry
    """
    vc = C.VIAL_CENTER
    r = C.VIAL_RADIUS + 0.3  # offset
    start_angle = math.pi  # label contacts from -X side
    max_angle = math.radians(C.LABEL_WRAP_ANGLE)

    tree = new_node_group(
        'PolarWrap',
        inputs=[
            ('Geometry', 'Geometry'),
            ('Wrap Factor', 'Float', 0.0),
            ('Blend Zone', 'Float', 5.0),
        ],
        outputs=[('Geometry', 'Geometry')]
    )

    nodes = tree.nodes
    links = tree.links
    group_in, group_out = get_group_io_nodes(tree)
    group_in.location = (-1200, 0)
    group_out.location = (1200, 0)

    # --- Get position ---
    pos = nodes.new('GeometryNodeInputPosition')
    pos.location = (-1000, -200)

    # Separate XYZ
    sep = nodes.new('ShaderNodeSeparateXYZ')
    sep.location = (-800, -200)
    links.new(pos.outputs['Position'], sep.inputs['Vector'])

    # --- Compute normalized U = x / wrap_length ---
    u_norm = nodes.new('ShaderNodeMath')
    u_norm.operation = 'DIVIDE'
    u_norm.location = (-600, -200)
    links.new(sep.outputs['X'], u_norm.inputs[0])
    u_norm.inputs[1].default_value = wrap_length

    # --- Compute angle = u * max_angle * wrap_factor ---
    # u * max_angle
    u_angle = nodes.new('ShaderNodeMath')
    u_angle.operation = 'MULTIPLY'
    u_angle.location = (-400, -200)
    links.new(u_norm.outputs['Value'], u_angle.inputs[0])
    u_angle.inputs[1].default_value = max_angle

    # * wrap_factor
    angle_scaled = nodes.new('ShaderNodeMath')
    angle_scaled.operation = 'MULTIPLY'
    angle_scaled.location = (-200, -200)
    links.new(u_angle.outputs['Value'], angle_scaled.inputs[0])
    links.new(group_in.outputs['Wrap Factor'], angle_scaled.inputs[1])

    # --- Blend factor: smoothstep based on how far along wrap_factor * wrap_length
    # vs vertex X position. Vertices beyond the current wrap extent stay flat.
    # blend = smoothstep(wrap_factor * wrap_length - blend_zone, wrap_factor * wrap_length, x)

    # wrap_factor * wrap_length = current wrap extent
    wrap_extent = nodes.new('ShaderNodeMath')
    wrap_extent.operation = 'MULTIPLY'
    wrap_extent.location = (-600, -400)
    links.new(group_in.outputs['Wrap Factor'], wrap_extent.inputs[0])
    wrap_extent.inputs[1].default_value = wrap_length

    # wrap_extent - blend_zone = blend_start
    blend_start = nodes.new('ShaderNodeMath')
    blend_start.operation = 'SUBTRACT'
    blend_start.location = (-400, -400)
    links.new(wrap_extent.outputs['Value'], blend_start.inputs[0])
    links.new(group_in.outputs['Blend Zone'], blend_start.inputs[1])

    # local_blend = (x - blend_start) / blend_zone, clamped 0-1
    x_minus_start = nodes.new('ShaderNodeMath')
    x_minus_start.operation = 'SUBTRACT'
    x_minus_start.location = (-200, -400)
    links.new(sep.outputs['X'], x_minus_start.inputs[0])
    links.new(blend_start.outputs['Value'], x_minus_start.inputs[1])

    blend_norm = nodes.new('ShaderNodeMath')
    blend_norm.operation = 'DIVIDE'
    blend_norm.location = (0, -400)
    links.new(x_minus_start.outputs['Value'], blend_norm.inputs[0])
    links.new(group_in.outputs['Blend Zone'], blend_norm.inputs[1])

    blend_clamp = nodes.new('ShaderNodeMath')
    blend_clamp.operation = 'MINIMUM'
    blend_clamp.location = (200, -400)
    links.new(blend_norm.outputs['Value'], blend_clamp.inputs[0])
    blend_clamp.inputs[1].default_value = 1.0

    blend_final = nodes.new('ShaderNodeMath')
    blend_final.operation = 'MAXIMUM'
    blend_final.location = (400, -400)
    links.new(blend_clamp.outputs['Value'], blend_final.inputs[0])
    blend_final.inputs[1].default_value = 0.0

    # Also zero out vertices beyond wrap extent (smoothly)
    # If x > wrap_extent, blend = 0 (vertex should disappear or stay at edge)
    beyond_check = nodes.new('ShaderNodeMath')
    beyond_check.operation = 'LESS_THAN'
    beyond_check.location = (200, -550)
    links.new(sep.outputs['X'], beyond_check.inputs[0])
    links.new(wrap_extent.outputs['Value'], beyond_check.inputs[1])

    blend_masked = nodes.new('ShaderNodeMath')
    blend_masked.operation = 'MULTIPLY'
    blend_masked.location = (600, -400)
    links.new(blend_final.outputs['Value'], blend_masked.inputs[0])
    links.new(beyond_check.outputs['Value'], blend_masked.inputs[1])

    # --- Compute wrapped position ---
    # start_angle - angle
    angle_neg = nodes.new('ShaderNodeMath')
    angle_neg.operation = 'SUBTRACT'
    angle_neg.location = (0, -100)
    angle_neg.inputs[0].default_value = start_angle
    links.new(angle_scaled.outputs['Value'], angle_neg.inputs[1])

    # cos(angle), sin(angle)
    cos_a = nodes.new('ShaderNodeMath')
    cos_a.operation = 'COSINE'
    cos_a.location = (200, -50)
    links.new(angle_neg.outputs['Value'], cos_a.inputs[0])

    sin_a = nodes.new('ShaderNodeMath')
    sin_a.operation = 'SINE'
    sin_a.location = (200, -150)
    links.new(angle_neg.outputs['Value'], sin_a.inputs[0])

    # wrapped_x = vial_cx + r * cos
    wx = nodes.new('ShaderNodeMath')
    wx.operation = 'MULTIPLY_ADD'
    wx.location = (400, -50)
    links.new(cos_a.outputs['Value'], wx.inputs[0])
    wx.inputs[1].default_value = r
    wx.inputs[2].default_value = vc[0]

    # wrapped_z = vial_cz + r * sin
    wz = nodes.new('ShaderNodeMath')
    wz.operation = 'MULTIPLY_ADD'
    wz.location = (400, -150)
    links.new(sin_a.outputs['Value'], wz.inputs[0])
    wz.inputs[1].default_value = r
    wz.inputs[2].default_value = vc[2]

    # wrapped_y = vial_cy + original_y
    wy = nodes.new('ShaderNodeMath')
    wy.operation = 'ADD'
    wy.location = (400, -250)
    links.new(sep.outputs['Y'], wy.inputs[0])
    wy.inputs[1].default_value = vc[1]

    # --- Lerp between flat position and wrapped position ---
    # flat pos: original (x + peel_edge_x, original_y + peel_edge_y, peel_edge_z)
    # Actually the mesh is already at peel edge via obj.location, so flat = original pos + obj origin
    # But GN works in local space, so flat = original local pos

    # lerp_x = mix(flat_x, wrapped_x, blend)
    # But flat_x is just the original X... and wrapped replaces it
    # We need: final = flat * (1-blend) + wrapped * blend
    # For X:
    flat_x_world = nodes.new('ShaderNodeMath')
    flat_x_world.operation = 'ADD'
    flat_x_world.location = (400, 100)
    links.new(sep.outputs['X'], flat_x_world.inputs[0])
    flat_x_world.inputs[1].default_value = C.PEEL_EDGE[0]

    lerp_x = nodes.new('ShaderNodeMath')
    lerp_x.operation = 'MULTIPLY_ADD'  # blend * (wrapped - flat) + flat
    lerp_x.location = (600, -50)
    # Actually use: flat + blend * (wrapped - flat) = flat * (1-blend) + wrapped * blend
    sub_x = nodes.new('ShaderNodeMath')
    sub_x.operation = 'SUBTRACT'
    sub_x.location = (500, 50)
    links.new(wx.outputs['Value'], sub_x.inputs[0])
    links.new(flat_x_world.outputs['Value'], sub_x.inputs[1])

    mix_x = nodes.new('ShaderNodeMath')
    mix_x.operation = 'MULTIPLY_ADD'
    mix_x.location = (700, -50)
    links.new(blend_masked.outputs['Value'], mix_x.inputs[0])
    links.new(sub_x.outputs['Value'], mix_x.inputs[1])
    links.new(flat_x_world.outputs['Value'], mix_x.inputs[2])

    # For Z:
    flat_z_world = nodes.new('ShaderNodeMath')
    flat_z_world.operation = 'ADD'
    flat_z_world.location = (400, -300)
    links.new(sep.outputs['Z'], flat_z_world.inputs[0])
    flat_z_world.inputs[1].default_value = C.PEEL_EDGE[2]

    sub_z = nodes.new('ShaderNodeMath')
    sub_z.operation = 'SUBTRACT'
    sub_z.location = (500, -200)
    links.new(wz.outputs['Value'], sub_z.inputs[0])
    links.new(flat_z_world.outputs['Value'], sub_z.inputs[1])

    mix_z = nodes.new('ShaderNodeMath')
    mix_z.operation = 'MULTIPLY_ADD'
    mix_z.location = (700, -150)
    links.new(blend_masked.outputs['Value'], mix_z.inputs[0])
    links.new(sub_z.outputs['Value'], mix_z.inputs[1])
    links.new(flat_z_world.outputs['Value'], mix_z.inputs[2])

    # For Y:
    flat_y_world = nodes.new('ShaderNodeMath')
    flat_y_world.operation = 'ADD'
    flat_y_world.location = (400, -350)
    links.new(sep.outputs['Y'], flat_y_world.inputs[0])
    flat_y_world.inputs[1].default_value = C.PEEL_EDGE[1]

    sub_y = nodes.new('ShaderNodeMath')
    sub_y.operation = 'SUBTRACT'
    sub_y.location = (500, -300)
    links.new(wy.outputs['Value'], sub_y.inputs[0])
    links.new(flat_y_world.outputs['Value'], sub_y.inputs[1])

    mix_y = nodes.new('ShaderNodeMath')
    mix_y.operation = 'MULTIPLY_ADD'
    mix_y.location = (700, -250)
    links.new(blend_masked.outputs['Value'], mix_y.inputs[0])
    links.new(sub_y.outputs['Value'], mix_y.inputs[1])
    links.new(flat_y_world.outputs['Value'], mix_y.inputs[2])

    # Combine XYZ → Set Position
    combine = nodes.new('ShaderNodeCombineXYZ')
    combine.location = (900, -100)
    links.new(mix_x.outputs['Value'], combine.inputs['X'])
    links.new(mix_y.outputs['Value'], combine.inputs['Y'])
    links.new(mix_z.outputs['Value'], combine.inputs['Z'])

    set_pos = nodes.new('GeometryNodeSetPosition')
    set_pos.location = (1050, 0)
    links.new(group_in.outputs['Geometry'], set_pos.inputs['Geometry'])
    links.new(combine.outputs['Vector'], set_pos.inputs['Position'])

    links.new(set_pos.outputs['Geometry'], group_out.inputs['Geometry'])

    return tree


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def setup_polar_wrap_driver(modifier, ctrl_obj, wrap_length):
    """Drive the GN Wrap Factor from CTRL.vial_rot_deg."""
    max_deg = C.LABEL_WRAP_ANGLE
    for key in modifier.keys():
        if 'Wrap' in key and 'Factor' in key:
            try:
                fc = modifier.driver_add(f'["{key}"]')
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


def setup_vial_rotation_driver(vial_obj, ctrl_obj):
    """Drive vial rotation from CTRL.vial_rot_deg."""
    fc = vial_obj.driver_add('rotation_euler', 1)
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
    """Keyframe CTRL for polar wrap demo."""
    ctrl_obj['vial_rot_deg'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=frame_start)
    ctrl_obj['vial_rot_deg'] = 270.0
    ctrl_obj.keyframe_insert(data_path='["vial_rot_deg"]', frame=frame_end)

    ctrl_obj['feed_mm'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=frame_start)
    ctrl_obj['feed_mm'] = 120.0
    ctrl_obj.keyframe_insert(data_path='["feed_mm"]', frame=frame_end)

    ctrl_obj['dancer_deg'] = 0.0
    ctrl_obj.keyframe_insert(data_path='["dancer_deg"]', frame=frame_start)

    set_linear_interpolation(ctrl_obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    objects = build_base_scene()
    ctrl = objects['ctrl']
    vial = objects['vial']

    # Create flat label mesh
    label_obj, wrap_length = create_flat_label_mesh()

    # Apply polar wrap GN
    wrap_group = create_polar_wrap_gn_group(wrap_length)
    wrap_mod = apply_gn_modifier(label_obj, wrap_group, 'PolarWrap')

    # Drivers
    setup_polar_wrap_driver(wrap_mod, ctrl, wrap_length)
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

    print(f"Rendering polar wrap: frames {frame_start}–{frame_end} to {out_dir}")
    render_animation()

    if args.encode_mp4:
        mp4 = encode_mp4(str(out_dir), fps=args.fps)
        if mp4:
            print(f"MP4: {mp4}")

    print("Done.")


if __name__ == '__main__':
    main()
