"""Set up camera, lighting, and render settings for product visualization.

Designed to be executed via blender-mcp's execute_blender_code tool,
after import_assembly.py has been run.
"""

import bpy
import math
from mathutils import Vector


def setup_camera():
    """Position camera for a 3/4 view of the assembly."""
    cam_data = bpy.data.cameras.new("ProductCamera")
    cam_data.lens = 50  # mm focal length
    cam_data.clip_end = 10  # 10m clip

    cam_obj = bpy.data.objects.new("ProductCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    # Position: elevated 3/4 view (assembly is ~200mm x 120mm at origin)
    # In Blender meters: 0.2m x 0.12m
    cam_obj.location = (0.3, -0.25, 0.2)

    # Point at assembly center
    target = Vector((0, 0, 0.025))  # ~25mm up
    direction = target - cam_obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()

    bpy.context.scene.camera = cam_obj
    return cam_obj


def setup_lighting():
    """Three-point lighting for product photography."""
    lights = []

    # Key light — warm, strong, from upper-right-front
    key = bpy.data.lights.new("KeyLight", type="AREA")
    key.energy = 50
    key.color = (1.0, 0.95, 0.9)
    key.size = 0.5
    key_obj = bpy.data.objects.new("KeyLight", key)
    key_obj.location = (0.3, -0.3, 0.4)
    key_obj.rotation_euler = (math.radians(45), 0, math.radians(30))
    bpy.context.scene.collection.objects.link(key_obj)
    lights.append(key_obj)

    # Fill light — cool, softer, from left
    fill = bpy.data.lights.new("FillLight", type="AREA")
    fill.energy = 20
    fill.color = (0.9, 0.95, 1.0)
    fill.size = 0.8
    fill_obj = bpy.data.objects.new("FillLight", fill)
    fill_obj.location = (-0.3, -0.2, 0.2)
    fill_obj.rotation_euler = (math.radians(60), 0, math.radians(-45))
    bpy.context.scene.collection.objects.link(fill_obj)
    lights.append(fill_obj)

    # Rim light — from behind, highlights edges
    rim = bpy.data.lights.new("RimLight", type="AREA")
    rim.energy = 30
    rim.color = (1.0, 1.0, 1.0)
    rim.size = 0.3
    rim_obj = bpy.data.objects.new("RimLight", rim)
    rim_obj.location = (-0.1, 0.3, 0.3)
    rim_obj.rotation_euler = (math.radians(-30), 0, math.radians(180))
    bpy.context.scene.collection.objects.link(rim_obj)
    lights.append(rim_obj)

    return lights


def setup_render_settings():
    """Configure render output for product shots."""
    scene = bpy.context.scene

    # Use Cycles for better quality
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True

    # Output
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.film_transparent = True  # transparent background

    # World: light grey environment
    world = bpy.data.worlds.new("ProductWorld")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.95, 0.95, 0.95, 1.0)
        bg_node.inputs["Strength"].default_value = 0.3
    scene.world = world


def setup_render():
    """Full render setup: camera + lights + settings."""
    setup_camera()
    setup_lighting()
    setup_render_settings()
    print("Render setup complete. Use F12 or Render > Render Image.")


setup_render()
