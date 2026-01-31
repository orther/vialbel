"""Geometry Nodes builder helpers for Blender 5.0.

Provides functions to programmatically create node groups and common patterns.
"""
import bpy
import math


def new_node_group(name, inputs=None, outputs=None):
    """Create a new Geometry Nodes group with specified inputs/outputs.

    Args:
        name: Node group name
        inputs: List of (name, type, default) tuples. Types: 'FLOAT', 'INT', 'VECTOR', 'GEOMETRY', etc.
        outputs: List of (name, type) tuples.

    Returns:
        The node group tree.
    """
    # Remove existing group with same name
    if name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[name])

    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')

    # Ensure Group Input and Group Output nodes exist
    has_input = any(n.type == 'GROUP_INPUT' for n in tree.nodes)
    has_output = any(n.type == 'GROUP_OUTPUT' for n in tree.nodes)
    if not has_input:
        tree.nodes.new('NodeGroupInput')
    if not has_output:
        tree.nodes.new('NodeGroupOutput')

    # Add sockets via the tree interface
    if inputs:
        for inp_name, inp_type, *default in inputs:
            socket = tree.interface.new_socket(
                name=inp_name,
                in_out='INPUT',
                socket_type=f'NodeSocket{inp_type}'
            )
            if default:
                socket.default_value = default[0]

    if outputs:
        for out_name, out_type in outputs:
            tree.interface.new_socket(
                name=out_name,
                in_out='OUTPUT',
                socket_type=f'NodeSocket{out_type}'
            )

    return tree


def get_group_io_nodes(tree):
    """Get the Group Input and Group Output nodes from a node tree."""
    input_node = None
    output_node = None
    for node in tree.nodes:
        if node.type == 'GROUP_INPUT':
            input_node = node
        elif node.type == 'GROUP_OUTPUT':
            output_node = node
    return input_node, output_node


def apply_gn_modifier(obj, node_group, name=None):
    """Apply a Geometry Nodes modifier to an object."""
    mod = obj.modifiers.new(name or node_group.name, 'NODES')
    mod.node_group = node_group
    return mod


def create_curve_to_ribbon_group(name="CurveToRibbon"):
    """Create a GN group that converts a curve to a ribbon mesh.

    Inputs:
        Geometry (curve)
        Width (float, default 40mm)
        Thickness (float, default 0.15mm)
    Output:
        Geometry (mesh ribbon)
    """
    tree = new_node_group(
        name,
        inputs=[
            ('Geometry', 'Geometry'),
            ('Width', 'Float', 40.0),
            ('Thickness', 'Float', 0.15),
        ],
        outputs=[('Geometry', 'Geometry')]
    )

    nodes = tree.nodes
    links = tree.links
    group_in, group_out = get_group_io_nodes(tree)
    group_in.location = (-400, 0)
    group_out.location = (400, 0)

    # Curve to Mesh with rectangle profile
    c2m = nodes.new('GeometryNodeCurveToMesh')
    c2m.location = (0, 0)

    # Rectangle profile via Quadrilateral node (Blender 5.0)
    rect = nodes.new('GeometryNodeCurvePrimitiveQuadrilateral')
    rect.mode = 'RECTANGLE'
    rect.location = (-200, -150)

    links.new(group_in.outputs['Geometry'], c2m.inputs['Curve'])
    links.new(rect.outputs['Curve'], c2m.inputs['Profile Curve'])
    links.new(group_in.outputs['Width'], rect.inputs['Width'])
    links.new(group_in.outputs['Thickness'], rect.inputs['Height'])
    links.new(c2m.outputs['Mesh'], group_out.inputs['Geometry'])

    return tree


def create_trim_reveal_group(name="TrimReveal"):
    """Create a GN group that trims/reveals a curve based on a factor.

    Uses Trim Curve to show only a portion of the curve,
    driven by a 0-1 factor (mapped from feed_mm externally).

    Inputs:
        Geometry (curve)
        Factor (float 0-1): how much of curve to reveal
    Output:
        Geometry (trimmed curve)
    """
    tree = new_node_group(
        name,
        inputs=[
            ('Geometry', 'Geometry'),
            ('Factor', 'Float', 1.0),
        ],
        outputs=[('Geometry', 'Geometry')]
    )

    nodes = tree.nodes
    links = tree.links
    group_in, group_out = get_group_io_nodes(tree)
    group_in.location = (-400, 0)
    group_out.location = (400, 0)

    trim = nodes.new('GeometryNodeTrimCurve')
    trim.location = (0, 0)
    trim.mode = 'FACTOR'

    links.new(group_in.outputs['Geometry'], trim.inputs['Curve'])
    # Start at 0, end at Factor
    links.new(group_in.outputs['Factor'], trim.inputs[3])  # End factor
    links.new(trim.outputs['Curve'], group_out.inputs['Geometry'])

    return tree
