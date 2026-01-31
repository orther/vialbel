"""Export all component STLs as 3MF files using trimesh.

Usage:
    python src/blender/export_3mf.py

Requires: pip install trimesh

Note: This script previously used Blender's 3MF exporter, but Blender 5.0+
removed the built-in 3MF add-on. trimesh provides a lightweight alternative
that produces valid 3MF files from STL input.
"""

import json
import os
import sys

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
        return [f for f in os.listdir(COMPONENTS_DIR) if f.endswith(".stl")]


def export_stl_as_3mf(stl_filename):
    """Load an STL and export as 3MF. Returns True on success."""
    import trimesh

    stl_path = os.path.join(COMPONENTS_DIR, stl_filename)
    if not os.path.exists(stl_path):
        print(f"  SKIP: {stl_path} not found")
        return False

    threemf_filename = stl_filename.replace(".stl", ".3mf")
    threemf_path = os.path.join(COMPONENTS_DIR, threemf_filename)

    try:
        mesh = trimesh.load(stl_path)
        mesh.export(threemf_path, file_type="3mf")
        size_kb = os.path.getsize(threemf_path) / 1024
        print(f"  OK: {threemf_filename} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  FAIL: {threemf_filename} — {e}")
        return False


def main():
    try:
        import trimesh  # noqa: F401
    except ImportError:
        print("ERROR: trimesh not installed. Run: pip install trimesh")
        sys.exit(1)

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
