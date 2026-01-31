"""
Label backing paper tension system components.

Models a spool holder, dancer arm, and guide roller bracket
for maintaining tension on label backing paper as it feeds
through the peel plate.
"""

from pathlib import Path

from build123d import *

from config import load_config

cfg = load_config()

# --- Parameters ---
spool_spindle_od = cfg["spool_spindle_od"]
spool_height = cfg["spool_height"]
spool_flange_diameter = cfg["spool_flange_diameter"]
spool_flange_thickness = cfg["spool_flange_thickness"]

dancer_arm_length = cfg["dancer_arm_length"]
dancer_arm_width = cfg["dancer_arm_width"]
dancer_arm_thickness = cfg["dancer_arm_thickness"]
pivot_bore = cfg["pivot_bore"]
bearing_od = cfg["bearing_od"]
bearing_id = cfg["bearing_id"]

mount_hole_diameter = cfg["mount_hole_diameter"]
wall_thickness = cfg["wall_thickness"]

bracket_base_width = cfg["bracket_base_width"]
bracket_base_depth = cfg["bracket_base_depth"]
bracket_height = cfg["bracket_height"]

# --- Output directory ---
output_dir = Path(__file__).resolve().parent.parent / "models" / "components"
output_dir.mkdir(parents=True, exist_ok=True)

# =====================
# 1. Spool Holder
# =====================
with BuildPart() as spool:
    # Base flange
    Cylinder(
        radius=spool_flange_diameter / 2,
        height=spool_flange_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # Spindle on top of flange
    with Locations([(0, 0, spool_flange_thickness)]):
        Cylinder(
            radius=spool_spindle_od / 2,
            height=spool_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    # M3 mounting hole through center of base
    with Locations([(0, 0, 0)]):
        Cylinder(
            radius=mount_hole_diameter / 2,
            height=spool_flange_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

# =====================
# 2. Dancer Arm
# =====================
pivot_hub_radius = pivot_bore / 2 + wall_thickness + 2  # extra meat around bore
roller_hub_radius = bearing_od / 2 + wall_thickness
spring_hole_offset = 10.0  # distance from pivot center

with BuildPart() as dancer:
    # Build arm profile as a 2D sketch, then extrude
    with BuildSketch():
        # Pivot hub circle
        Circle(radius=pivot_hub_radius)
        # Roller hub circle
        with Locations([(dancer_arm_length, 0)]):
            Circle(radius=roller_hub_radius)
        # Connecting rectangle
        with Locations([(dancer_arm_length / 2, 0)]):
            Rectangle(dancer_arm_length, dancer_arm_width)
    extrude(amount=dancer_arm_thickness)
    # Pivot bore
    Cylinder(
        radius=pivot_bore / 2,
        height=dancer_arm_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.SUBTRACT,
    )
    # Bearing bore at roller end
    with Locations([(dancer_arm_length, 0, 0)]):
        Cylinder(
            radius=bearing_id / 2,
            height=dancer_arm_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )
    # Spring attachment hole near pivot
    with Locations([(spring_hole_offset, dancer_arm_width / 2 - 1.5, 0)]):
        Cylinder(
            radius=1.5,  # 3mm diameter
            height=dancer_arm_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

# =====================
# 3. Guide Roller Bracket
# =====================
with BuildPart() as bracket:
    # Horizontal base plate
    Box(
        length=bracket_base_width,
        width=bracket_base_depth,
        height=wall_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    # Vertical wall (L-shape)
    with Locations([(0, -bracket_base_depth / 2 + wall_thickness / 2, wall_thickness)]):
        Box(
            length=bracket_base_width,
            width=wall_thickness,
            height=bracket_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    # Roller pin hole at top of vertical wall
    vertical_wall_y = -bracket_base_depth / 2 + wall_thickness / 2
    hole_z = wall_thickness + bracket_height - bearing_od / 2 - 2
    with BuildSketch(
        Plane(
            origin=(0, vertical_wall_y - wall_thickness / 2, hole_z),
            x_dir=(1, 0, 0),
            z_dir=(0, -1, 0),
        )
    ):
        Circle(radius=pivot_bore / 2)
    extrude(amount=wall_thickness, mode=Mode.SUBTRACT)

    # Two M3 mounting holes in base, 15mm apart
    hole_spacing = 15.0
    for x_off in [-hole_spacing / 2, hole_spacing / 2]:
        with Locations([(x_off, 0, 0)]):
            Cylinder(
                radius=mount_hole_diameter / 2,
                height=wall_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

# =====================
# Export
# =====================
components = [
    ("spool_holder", spool),
    ("dancer_arm", dancer),
    ("guide_roller_bracket", bracket),
]

for name, comp in components:
    part = comp.part
    bb = part.bounding_box()
    sz = bb.size
    print(f"{name}: bounding box {sz.X:.1f} x {sz.Y:.1f} x {sz.Z:.1f} mm")

    stl_path = str(output_dir / f"{name}.stl")
    export_stl(part, stl_path)
    print(f"  Exported: {stl_path}")

    mf_path = str(output_dir / f"{name}.3mf")
    try:
        exporter = Mesher()
        exporter.add_shape(part)
        exporter.write(mf_path)
        print(f"  Exported: {mf_path}")
    except Exception as e:
        print(f"  3mf export skipped ({e}), STL is primary format")

print("\nAll components exported successfully.")
