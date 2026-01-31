"""Render configuration and execution for headless Blender."""
import bpy
import os
import subprocess
from pathlib import Path


def setup_render(scene=None, engine='CYCLES', samples=64,
                 resolution=(1920, 1080), fps=24, frame_range=(1, 120)):
    """Configure render settings for headless operation."""
    if scene is None:
        scene = bpy.context.scene

    # Engine
    scene.render.engine = engine

    if engine == 'CYCLES':
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.seed = 0  # Fixed seed for determinism
        scene.cycles.use_animated_seed = False
        # Note: GPU rendering (Metal/CUDA) is NOT bit-reproducible due to
        # floating-point non-determinism. For strict determinism, use CPU:
        #   scene.cycles.device = 'CPU'
        # Use GPU if available, fall back to CPU
        prefs = bpy.context.preferences.addons.get('cycles')
        if prefs:
            prefs.preferences.compute_device_type = 'METAL'  # macOS
            prefs.preferences.get_devices()
            for d in prefs.preferences.devices:
                d.use = True
        scene.cycles.device = 'GPU'
    elif engine == 'BLENDER_EEVEE':
        scene.eevee.taa_render_samples = samples

    # Resolution
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100

    # Frame range
    scene.frame_start = frame_range[0]
    scene.frame_end = frame_range[1]
    scene.render.fps = fps

    # Output format
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 15

    # Film transparency for compositing
    scene.render.film_transparent = False


def setup_output(scene=None, output_dir='./output'):
    """Configure output path."""
    if scene is None:
        scene = bpy.context.scene
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out / 'frame_')
    return out


def render_animation(scene=None):
    """Render full animation."""
    if scene is None:
        scene = bpy.context.scene
    bpy.ops.render.render(animation=True)


def render_frame(scene=None, frame=1):
    """Render a single frame."""
    if scene is None:
        scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)


def set_linear_interpolation(obj):
    """Set all keyframe interpolation to LINEAR for an object.

    Compatible with Blender 5.0 layered action API.
    """
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    # Blender 5.0: layered actions — fcurves are in channelbags
    if hasattr(action, 'layers') and action.layers:
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'
    # Legacy fallback
    elif hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def encode_mp4(output_dir, fps=24, output_name='animation.mp4'):
    """Encode PNG frames to MP4 using ffmpeg."""
    out = Path(output_dir)
    pattern = str(out / 'frame_%04d.png')
    mp4_path = str(out / output_name)
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', pattern,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '18',
        mp4_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return mp4_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"MP4 encoding failed: {e}")
        return None
