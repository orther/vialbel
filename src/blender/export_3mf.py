"""Export all component STLs as 3MF files using Blender.

Usage:
    blender --background --python src/blender/export_3mf.py

Blender produces reliable manifold 3MF from STL imports, avoiding
the non-manifold issues that can occur with Build123d's Mesher.
"""

import json
import os
import sys

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
COMPONENTS_DIR = os.path.join(PROJECT_ROOT, "models", "components")
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "models", "assembly_manifest.json")


def get_stl_files():
    """Get STL file list from manifest, falling back to directory listing."""
    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
        return [entry["file"] for entry in manifest if entry["file"].endswith(".stl")]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # Fallback: list all STLs in components dir
        return [f for f in os.listdir(COMPONENTS_DIR) if f.endswith(".stl")]


def clear_scene():
    """Remove all objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def export_stl_as_3mf(stl_filename):
    """Import an STL and export as 3MF. Returns True on success."""
    stl_path = os.path.join(COMPONENTS_DIR, stl_filename)
    if not os.path.exists(stl_path):
        print(f"  SKIP: {stl_path} not found")
        return False

    clear_scene()

    # Import STL
    bpy.ops.wm.stl_import(filepath=stl_path)
    obj = bpy.context.active_object
    if obj is None:
        print(f"  FAIL: No object created from {stl_filename}")
        return False

    # Select only this object
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export as 3MF
    threemf_filename = stl_filename.replace(".stl", ".3mf")
    threemf_path = os.path.join(COMPONENTS_DIR, threemf_filename)

    try:
        bpy.ops.export_mesh.threemf(filepath=threemf_path)
        size_kb = os.path.getsize(threemf_path) / 1024
        print(f"  OK: {threemf_filename} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  FAIL: {threemf_filename} — {e}")
        return False


def main():
    stl_files = get_stl_files()
    print(f"Exporting {len(stl_files)} components as 3MF...\n")

    success = 0
    for stl_file in stl_files:
        print(f"{stl_file}:")
        if export_stl_as_3mf(stl_file):
            success += 1

    print(f"\n{success}/{len(stl_files)} components exported as 3MF.")
    if success < len(stl_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
