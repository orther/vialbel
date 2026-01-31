"""
Label path geometry — defines the physical routing of label backing paper
through the machine from spool to vial surface.

Path: Spool exit → Dancer roller → Guide roller → Peel plate entry → Peel edge → Vial

Generates a 3D visualization of the path and validates geometric constraints
(minimum bend radius, clearances, total path length).
"""

import math
from dataclasses import dataclass
from pathlib import Path

from build123d import *

from config import load_config

cfg = load_config()

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
# Label stock properties
LABEL_WIDTH = cfg["label_width"]
LABEL_THICKNESS = cfg["label_thickness"]
MIN_BEND_RADIUS = cfg["min_bend_radius"]

# Component positions (from frame.py)
# TODO: Source these values from models/assembly_manifest.json instead of
# recomputing them here.  This would make frame.py the single source of truth
# for all component positions across the project.
BASE_THICKNESS = cfg["base_thickness"]
WALL_HEIGHT = cfg["frame_wall_height"]
WALL_THICKNESS = cfg["frame_wall_thickness"]
BASE_LENGTH = cfg["frame_length"]
BASE_WIDTH = cfg["frame_width"]

# Peel plate
PEEL_WALL_X = BASE_LENGTH / 2 - WALL_THICKNESS / 2 - 5.0
PEEL_MOUNT_Z = WALL_HEIGHT / 2 + BASE_THICKNESS
PEEL_EDGE_X = PEEL_WALL_X - 25.0 / 2 - WALL_THICKNESS / 2 + 25.0 / 2
PEEL_EDGE_Z = PEEL_MOUNT_Z  # label exits at peel edge height

# Vial cradle
CRADLE_X = PEEL_WALL_X - 35.0
CRADLE_Y = 25.0
VIAL_DIAMETER = cfg["vial_diameter"]
VIAL_CENTER_Z = (
    BASE_THICKNESS + cfg["cradle_v_block_height"]
)  # top of V-block where vial sits

# Spool holder
SPOOL_X = -BASE_LENGTH / 2 + 30.0
SPOOL_Y = -BASE_WIDTH / 2 + 30.0
SPOOL_EXIT_Z = BASE_THICKNESS + cfg["spool_flange_thickness"] + cfg["spool_height"] / 2

# Dancer arm
DANCER_X = -BASE_LENGTH / 2 + 80.0
DANCER_Y = -BASE_WIDTH / 2 + 35.0
DANCER_ARM_LENGTH = cfg["dancer_arm_length"]
PIVOT_POST_HEIGHT = 40.0
DANCER_ROLLER_Z = BASE_THICKNESS + PIVOT_POST_HEIGHT + cfg["dancer_arm_thickness"] / 2

# Guide roller bracket
GUIDE_X = PEEL_WALL_X - 70.0
GUIDE_Y = -BASE_WIDTH / 2 + 25.0
GUIDE_ROLLER_Z = BASE_THICKNESS + cfg["bracket_height"] - cfg["bearing_od"] / 2 - 2.0


# ---------------------------------------------------------------------------
# Path waypoints
# ---------------------------------------------------------------------------
@dataclass
class Waypoint:
    """A point along the label path."""

    name: str
    x: float
    y: float
    z: float
    wrap_angle: float = 0.0  # degrees of wrap around a roller at this point
    roller_radius: float = 0.0  # radius of roller/edge at this point


def build_waypoints() -> list[Waypoint]:
    """Define the label path waypoints from spool to vial."""
    # Dancer roller is at the end of the arm, pointing toward the guide roller
    dancer_roller_x = DANCER_X + DANCER_ARM_LENGTH * 0.7  # arm angles toward path
    dancer_roller_y = DANCER_Y + 10.0

    return [
        Waypoint(
            name="spool_exit",
            x=SPOOL_X,
            y=SPOOL_Y,
            z=SPOOL_EXIT_Z,
        ),
        Waypoint(
            name="dancer_roller",
            x=dancer_roller_x,
            y=dancer_roller_y,
            z=DANCER_ROLLER_Z,
            wrap_angle=90.0,
            roller_radius=11.0,  # bearing_od/2
        ),
        Waypoint(
            name="guide_roller",
            x=GUIDE_X,
            y=GUIDE_Y,
            z=GUIDE_ROLLER_Z,
            wrap_angle=45.0,
            roller_radius=11.0,
        ),
        Waypoint(
            name="peel_entry",
            x=PEEL_WALL_X - 25.0,
            y=0.0,
            z=PEEL_EDGE_Z + 5.0,
        ),
        Waypoint(
            name="peel_edge",
            x=PEEL_WALL_X - 12.5,
            y=0.0,
            z=PEEL_EDGE_Z,
            wrap_angle=160.0,
            roller_radius=1.0,  # 2mm diameter peel edge
        ),
        Waypoint(
            name="vial_contact",
            x=CRADLE_X,
            y=CRADLE_Y,
            z=VIAL_CENTER_Z,
            wrap_angle=270.0,
            roller_radius=VIAL_DIAMETER / 2,
        ),
    ]


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------
def segment_length(a: Waypoint, b: Waypoint) -> float:
    """Euclidean distance between two waypoints."""
    return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2)


def validate_path(waypoints: list[Waypoint]) -> list[str]:
    """Validate path constraints. Returns list of issues (empty = pass)."""
    issues = []

    # Check bend radii at each roller
    for wp in waypoints:
        if wp.roller_radius > 0 and wp.roller_radius < MIN_BEND_RADIUS:
            if wp.name == "peel_edge":
                # Peel edge is intentionally sharp — this is the separation point
                continue
            issues.append(
                f"{wp.name}: roller radius {wp.roller_radius:.1f}mm "
                f"< minimum {MIN_BEND_RADIUS:.1f}mm"
            )

    # Check total path length is reasonable (should be 300-800mm for this machine)
    total_length = 0.0
    for i in range(len(waypoints) - 1):
        seg = segment_length(waypoints[i], waypoints[i + 1])
        total_length += seg
        # Add arc length at wrap points
        if waypoints[i + 1].roller_radius > 0 and waypoints[i + 1].wrap_angle > 0:
            arc = (
                (waypoints[i + 1].wrap_angle / 360.0)
                * 2
                * math.pi
                * waypoints[i + 1].roller_radius
            )
            total_length += arc

    if total_length < 200.0:
        issues.append(f"Total path length {total_length:.1f}mm seems too short")
    if total_length > 1000.0:
        issues.append(f"Total path length {total_length:.1f}mm seems too long")

    # Check no segment crosses through the base plate (Z < 0)
    for wp in waypoints:
        if wp.z < BASE_THICKNESS:
            issues.append(
                f"{wp.name}: Z={wp.z:.1f}mm is below base plate top ({BASE_THICKNESS}mm)"
            )

    return issues, total_length


# ---------------------------------------------------------------------------
# Path visualization (3D)
# ---------------------------------------------------------------------------
def build_path_visualization(waypoints: list[Waypoint]) -> Part:
    """Create a 3D tube following the label path for visualization."""
    tube_radius = LABEL_THICKNESS * 5  # exaggerated for visibility

    # Build path as a series of line segments with spheres at waypoints
    with BuildPart() as path_viz:
        for i, wp in enumerate(waypoints):
            # Sphere at each waypoint
            with Locations([(wp.x, wp.y, wp.z)]):
                Sphere(radius=2.0)

            # Tube segment to next waypoint
            if i < len(waypoints) - 1:
                next_wp = waypoints[i + 1]
                dx = next_wp.x - wp.x
                dy = next_wp.y - wp.y
                dz = next_wp.z - wp.z
                length = math.sqrt(dx * dx + dy * dy + dz * dz)

                if length < 0.1:
                    continue

                mid_x = (wp.x + next_wp.x) / 2
                mid_y = (wp.y + next_wp.y) / 2
                mid_z = (wp.z + next_wp.z) / 2

                # Create cylinder along segment
                with BuildPart() as seg:
                    Cylinder(radius=tube_radius, height=length)

                # Calculate rotation to align cylinder with segment direction
                # Default cylinder is along Z axis
                seg_part = seg.part

                # Compute rotation angles
                horiz = math.sqrt(dx * dx + dy * dy)
                pitch = math.degrees(math.atan2(horiz, dz))
                yaw = math.degrees(math.atan2(dy, dx))

                # Apply rotations: first pitch around Y, then yaw around Z
                seg_part = seg_part.rotate(Axis.Y, pitch)
                seg_part = seg_part.rotate(Axis.Z, yaw)
                seg_part = seg_part.move(Location((mid_x, mid_y, mid_z)))

                add(seg_part)

    return path_viz.part


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
output_dir = Path(__file__).resolve().parent.parent / "models" / "components"
output_dir.mkdir(parents=True, exist_ok=True)

waypoints = build_waypoints()

# Print path report
print("Label Path Analysis")
print("=" * 60)
print(
    f"\nLabel: {LABEL_WIDTH}mm x {LABEL_THICKNESS}mm, min bend radius: {MIN_BEND_RADIUS}mm"
)
print("\nWaypoints:")
for i, wp in enumerate(waypoints):
    wrap_info = (
        f", wrap={wp.wrap_angle:.0f}°, R={wp.roller_radius:.1f}mm"
        if wp.roller_radius > 0
        else ""
    )
    print(f"  {i + 1}. {wp.name}: ({wp.x:.1f}, {wp.y:.1f}, {wp.z:.1f}){wrap_info}")

print("\nSegment lengths:")
for i in range(len(waypoints) - 1):
    seg = segment_length(waypoints[i], waypoints[i + 1])
    print(f"  {waypoints[i].name} → {waypoints[i + 1].name}: {seg:.1f}mm")

issues, total_length = validate_path(waypoints)
print(f"\nTotal path length: {total_length:.1f}mm")

if issues:
    print(f"\nValidation FAILED ({len(issues)} issues):")
    for issue in issues:
        print(f"  ✗ {issue}")
else:
    print("\nValidation PASSED — all constraints satisfied")

# Build and export visualization
print("\nBuilding path visualization...")
try:
    path_part = build_path_visualization(waypoints)
    bb = path_part.bounding_box()
    print(
        f"Path visualization bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm"
    )

    stl_path = str(output_dir / "label_path.stl")
    export_stl(path_part, stl_path, tolerance=0.01, angular_tolerance=0.1)
    print(f"Exported: {stl_path}")
except Exception as e:
    print(f"Path visualization export failed: {e}")
    print("(Path analysis and validation still completed successfully)")

print("\nLabel path analysis complete.")
