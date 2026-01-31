"""Configure Blender scene units to millimeters."""
import bpy


def setup_units(scene=None):
    """Set scene to metric millimeters."""
    if scene is None:
        scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001  # 1 BU = 1mm
    scene.unit_settings.length_unit = 'MILLIMETERS'
