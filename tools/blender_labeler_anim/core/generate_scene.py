"""Shared scene generation: camera, lights, ground plane, CTRL empty."""
import bpy
import math
from . import constants as C
from .units import setup_units
from .materials import create_glass_material, create_metal_material


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Clear orphan data
    for block in bpy.data.meshes:
        if not block.users:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if not block.users:
            bpy.data.materials.remove(block)
    for block in bpy.data.curves:
        if not block.users:
            bpy.data.curves.remove(block)


def create_ctrl_empty():
    """Create the CTRL empty with custom properties for animation control."""
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    ctrl = bpy.context.active_object
    ctrl.name = 'CTRL'

    # Custom properties with sensible defaults
    ctrl['feed_mm'] = 0.0
    ctrl['vial_rot_deg'] = 0.0
    ctrl['dancer_deg'] = 0.0

    # Set property ranges via id_properties_ui (Blender 3.0+)
    ui = ctrl.id_properties_ui('feed_mm')
    ui.update(min=0.0, max=200.0, soft_min=0.0, soft_max=150.0, description="Label feed distance in mm")

    ui = ctrl.id_properties_ui('vial_rot_deg')
    ui.update(min=0.0, max=360.0, soft_min=0.0, soft_max=270.0, description="Vial rotation in degrees")

    ui = ctrl.id_properties_ui('dancer_deg')
    ui.update(min=-30.0, max=30.0, soft_min=-20.0, soft_max=20.0, description="Dancer arm angle in degrees")

    return ctrl


def create_camera(location=(200, -180, 120), target=(40, 0, 20)):
    """Create and aim a camera at the mechanism."""
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 50
    cam_data.clip_start = 1  # mm
    cam_data.clip_end = 10000

    cam = bpy.data.objects.new('Camera', cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location

    # Point at target using track-to constraint
    track = cam.constraints.new('TRACK_TO')
    target_empty = bpy.data.objects.new('CameraTarget', None)
    target_empty.location = target
    bpy.context.scene.collection.objects.link(target_empty)
    target_empty.hide_set(True)

    track.target = target_empty
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam
    return cam


def create_lighting():
    """Create a 3-point lighting setup."""
    lights = []

    # Key light
    key_data = bpy.data.lights.new('KeyLight', 'AREA')
    key_data.energy = 5000000  # High wattage for mm-scale scene (scale_length=0.001)
    key_data.size = 100
    key = bpy.data.objects.new('KeyLight', key_data)
    key.location = (150, -100, 200)
    key.rotation_euler = (math.radians(45), 0, math.radians(30))
    bpy.context.scene.collection.objects.link(key)
    lights.append(key)

    # Fill light
    fill_data = bpy.data.lights.new('FillLight', 'AREA')
    fill_data.energy = 2500000
    fill_data.size = 80
    fill = bpy.data.objects.new('FillLight', fill_data)
    fill.location = (-100, -80, 100)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-45))
    bpy.context.scene.collection.objects.link(fill)
    lights.append(fill)

    # Rim light
    rim_data = bpy.data.lights.new('RimLight', 'AREA')
    rim_data.energy = 3000000
    rim_data.size = 60
    rim = bpy.data.objects.new('RimLight', rim_data)
    rim.location = (-50, 150, 150)
    rim.rotation_euler = (math.radians(30), 0, math.radians(180))
    bpy.context.scene.collection.objects.link(rim)
    lights.append(rim)

    return lights


def create_ground_plane():
    """Create a ground plane for shadow catching."""
    bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = 'GroundPlane'

    mat = bpy.data.materials.new('GroundMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.95, 0.95, 0.95, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.9
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    ground.data.materials.append(mat)

    return ground


def create_vial():
    """Create a glass vial at the correct position and orientation."""
    r = C.VIAL_RADIUS
    # Vial height along Y (cylinder axis = Y after rotation)
    vial_length = 38.5  # mm, typical 2mL vial

    bpy.ops.mesh.primitive_cylinder_add(
        radius=r,
        depth=vial_length,
        location=C.VIAL_CENTER,
        vertices=32,
    )
    vial = bpy.context.active_object
    vial.name = 'Vial'
    # Rotate 90° about X so cylinder axis aligns with Y
    vial.rotation_euler = (math.radians(90), 0, 0)

    mat = create_glass_material()
    vial.data.materials.append(mat)

    # Smooth shading via mesh attribute
    for poly in vial.data.polygons:
        poly.use_smooth = True

    return vial


def create_peel_plate():
    """Create a simplified peel plate geometry at the peel edge."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(C.PEEL_EDGE[0], C.PEEL_EDGE[1], C.PEEL_EDGE[2] - 5))
    plate = bpy.context.active_object
    plate.name = 'PeelPlate'
    plate.scale = (15, 3, 10)

    mat = create_metal_material('PeelPlateMat', (0.7, 0.7, 0.72, 1.0))
    plate.data.materials.append(mat)
    return plate


def create_rollers():
    """Create dancer and guide roller cylinders."""
    rollers = []
    for name, center, radius in [
        ('DancerRoller', C.DANCER_ROLLER_CENTER, C.DANCER_ROLLER_RADIUS),
        ('GuideRoller', C.GUIDE_ROLLER_CENTER, C.GUIDE_ROLLER_RADIUS),
    ]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius, depth=25, location=center, vertices=24
        )
        roller = bpy.context.active_object
        roller.name = name
        # Roller axis along Y
        roller.rotation_euler = (math.radians(90), 0, 0)
        mat = create_metal_material(f'{name}Mat')
        roller.data.materials.append(mat)
        for poly in roller.data.polygons:
            poly.use_smooth = True
        rollers.append(roller)
    return rollers


def build_base_scene():
    """Build the complete base scene with all shared elements.

    Returns dict of created objects.
    """
    clear_scene()
    setup_units()

    objects = {}
    objects['ctrl'] = create_ctrl_empty()
    objects['camera'] = create_camera()
    objects['lights'] = create_lighting()
    objects['ground'] = create_ground_plane()
    objects['vial'] = create_vial()
    objects['peel_plate'] = create_peel_plate()
    objects['rollers'] = create_rollers()

    return objects
