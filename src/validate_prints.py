#!/usr/bin/env python3
"""Validate STL files for 3D printability: manifold, overhang, and wall thickness checks."""

import sys
from pathlib import Path

try:
    import trimesh
    import numpy as np
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install trimesh numpy")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_DIR = PROJECT_ROOT / "models" / "components"

COMPONENT_FILES = [
    "main_frame.stl",
    "peel_plate.stl",
    "vial_cradle.stl",
    "spool_holder.stl",
    "dancer_arm.stl",
    "guide_roller_bracket.stl",
]

MIN_WALL_THICKNESS_MM = 0.8
MAX_OVERHANG_RATIO = 0.50  # 50% — generous for parts with cylinders, fillets, V-grooves
OVERHANG_ANGLE_DEG = 45.0


def check_manifold(mesh):
    """Check if mesh is watertight and represents a valid volume."""
    issues = []
    if not mesh.is_watertight:
        issues.append("Not watertight")
    if not mesh.is_volume:
        issues.append("Not a valid volume")
    return issues


def check_overhangs(mesh):
    """Compute percentage of surface area with overhang > 45 degrees from vertical."""
    z_up = np.array([0.0, 0.0, 1.0])
    normals = mesh.face_normals
    # Angle between face normal and Z-up
    cos_angles = np.dot(normals, z_up)
    # Overhang faces point downward: normal has negative Z component
    # and the angle from vertical exceeds threshold.
    # A face is "overhang" if the angle between its normal and -Z is < 45 deg,
    # i.e., the face points mostly downward.
    # Equivalently: angle from Z-up > (180 - 45) = 135 deg, meaning cos < cos(135)
    # But the standard definition: overhang = angle from build plate normal (Z) > 90+45=135?
    # Simpler: a face needs support if its normal's Z component < -cos(45deg)
    threshold = -np.cos(np.radians(OVERHANG_ANGLE_DEG))
    face_areas = mesh.area_faces
    overhang_mask = cos_angles < threshold
    overhang_area = face_areas[overhang_mask].sum()
    total_area = face_areas.sum()
    ratio = overhang_area / total_area if total_area > 0 else 0.0
    return ratio


def check_wall_thickness(mesh):
    """Estimate minimum wall thickness using ray casting from face centroids inward."""
    # Sample a subset of faces for performance
    n_samples = min(500, len(mesh.faces))
    rng = np.random.default_rng(42)
    indices = rng.choice(len(mesh.faces), size=n_samples, replace=False)

    centroids = mesh.triangles_center[indices]
    normals = mesh.face_normals[indices]

    # Cast rays inward (opposite of face normal)
    ray_directions = -normals

    # Use ray-mesh intersection
    locations, index_ray, index_tri = mesh.ray.intersects_location(
        ray_origins=centroids + ray_directions * 0.001,  # offset slightly to avoid self-hit
        ray_directions=ray_directions,
    )

    if len(locations) == 0:
        return None  # Can't determine

    # For each ray that hit, compute distance
    distances = np.linalg.norm(locations - centroids[index_ray], axis=1)

    # Filter out very small distances (self-intersection artifacts)
    valid = distances > 0.01  # 0.01mm
    if not valid.any():
        return None

    return float(distances[valid].min())


def validate_component(filepath):
    """Run all checks on a single STL file. Returns (passed, report_lines)."""
    mesh = trimesh.load(filepath, force="mesh")
    name = filepath.name
    lines = []
    passed = True

    # Manifold
    manifold_issues = check_manifold(mesh)
    if manifold_issues:
        lines.append(f"  FAIL Manifold: {', '.join(manifold_issues)}")
        passed = False
    else:
        lines.append("  PASS Manifold: watertight and valid volume")

    # Overhangs
    overhang_ratio = check_overhangs(mesh)
    overhang_pct = overhang_ratio * 100
    if overhang_ratio > MAX_OVERHANG_RATIO:
        lines.append(f"  FAIL Overhang: {overhang_pct:.1f}% unsupported (max {MAX_OVERHANG_RATIO*100:.0f}%)")
        passed = False
    else:
        lines.append(f"  PASS Overhang: {overhang_pct:.1f}% unsupported")

    # Wall thickness
    try:
        min_wall = check_wall_thickness(mesh)
        if min_wall is None:
            lines.append("  SKIP Wall thickness: could not determine")
        elif min_wall < MIN_WALL_THICKNESS_MM:
            lines.append(f"  FAIL Wall thickness: {min_wall:.2f}mm (min {MIN_WALL_THICKNESS_MM}mm)")
            passed = False
        else:
            lines.append(f"  PASS Wall thickness: {min_wall:.2f}mm")
    except Exception as e:
        lines.append(f"  SKIP Wall thickness: {e}")

    return passed, lines


def main():
    all_passed = True
    missing = []

    for filename in COMPONENT_FILES:
        filepath = COMPONENTS_DIR / filename
        if not filepath.exists():
            print(f"\n{filename}: MISSING")
            missing.append(filename)
            all_passed = False
            continue

        passed, lines = validate_component(filepath)
        status = "PASS" if passed else "FAIL"
        print(f"\n{filename}: {status}")
        for line in lines:
            print(line)
        if not passed:
            all_passed = False

    if missing:
        print(f"\nMissing files: {', '.join(missing)}")

    print(f"\n{'='*40}")
    if all_passed:
        print("All components passed validation.")
    else:
        print("Some components failed validation.")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
