"""Main frame for the vial label applicator.

A flat base plate with vertical mounting walls and slots for adjustable
positioning of all label applicator components: peel plate, vial cradle,
spool holder, dancer arm pivot, and guide roller bracket.

Layout (top view, X = left-right, Y = front-back):

    [Spool]     [Dancer pivot]     [Guide bracket]
       |              |                   |
       +--- paper path ---> [Peel plate] ---> label out
                                              |
                                        [Vial cradle]
"""

from pathlib import Path

from build123d import *

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
base_length = 200.0  # mm - X dimension
base_width = 120.0  # mm - Y dimension
base_thickness = 5.0  # mm - Z
wall_height = 30.0  # mm
wall_thickness = 4.0  # mm
heat_insert_od = 4.0  # mm - heat-set insert outer diameter
heat_insert_depth = 5.0  # mm
slot_length = 10.0  # mm - adjustment slot (+-5mm)
slot_width = 3.4  # mm - M3 clearance slot
pivot_post_od = 8.0  # mm
pivot_post_height = 40.0  # mm
fillet_radius = 2.0  # mm
m3_hole = 3.2  # mm - M3 clearance

# ---------------------------------------------------------------------------
# Component positions (origin at base plate center)
# X: left(-) to right(+), Y: back(-) to front(+)
# ---------------------------------------------------------------------------
# Peel plate mounts on a wall at the right end of the frame.
# The wall is near X = +base_length/2, centered on Y.
peel_wall_x = base_length / 2 - wall_thickness / 2 - 5.0  # 5mm inset from edge
peel_wall_y = 0.0
peel_mount_spacing = 30.0  # matches peel_plate mount_hole_spacing
peel_mount_z = wall_height / 2 + base_thickness  # vertical center of wall

# Vial cradle sits adjacent to peel plate output, shifted toward front (+Y).
# Two pairs of adjustment slots on the base plate.
cradle_center_x = peel_wall_x - 35.0  # ~30mm left of peel wall
cradle_center_y = 25.0  # front side of base
cradle_slot_spacing_x = 36.0  # along X
cradle_slot_spacing_y = 20.0  # along Y

# Spool holder at back-left corner.
spool_x = -base_length / 2 + 30.0
spool_y = -base_width / 2 + 30.0
spool_mount_hole_diameter = m3_hole

# Dancer arm pivot post between spool and peel plate.
dancer_x = -base_length / 2 + 80.0
dancer_y = -base_width / 2 + 35.0

# Guide roller bracket between dancer and peel plate.
guide_x = peel_wall_x - 70.0
guide_y = -base_width / 2 + 25.0
guide_mount_spacing = 15.0  # matches bracket hole spacing

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
output_dir = Path(__file__).resolve().parent.parent / "models" / "components"
output_dir.mkdir(parents=True, exist_ok=True)
assembly_dir = Path(__file__).resolve().parent.parent / "models" / "assembly"
assembly_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Build the main frame
# ---------------------------------------------------------------------------
with BuildPart() as frame:
    # --- Base plate ---
    Box(
        base_length,
        base_width,
        base_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # --- Peel plate mounting wall ---
    # Vertical wall at the right end, full width of base, rising from base top.
    with Locations([(peel_wall_x, peel_wall_y, base_thickness)]):
        Box(
            wall_thickness,
            base_width * 0.5,  # half-width wall for peel plate
            wall_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Heat-set insert holes in the peel plate wall (blind holes from front face).
    # Holes go into the wall along -X direction (into the wall from its right face).
    for y_off in [-peel_mount_spacing / 2, peel_mount_spacing / 2]:
        wall_face_x = peel_wall_x + wall_thickness / 2
        with Locations([(wall_face_x, peel_wall_y + y_off, peel_mount_z)]):
            Cylinder(
                radius=heat_insert_od / 2,
                height=heat_insert_depth,
                rotation=(0, -90, 0),
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    # --- Vial cradle adjustment slots ---
    # Two pairs of slots on the base plate for M3 bolts with +-5mm adjustment.
    cradle_slot_positions = [
        (cradle_center_x - cradle_slot_spacing_x / 2, cradle_center_y - cradle_slot_spacing_y / 2),
        (cradle_center_x + cradle_slot_spacing_x / 2, cradle_center_y - cradle_slot_spacing_y / 2),
        (cradle_center_x - cradle_slot_spacing_x / 2, cradle_center_y + cradle_slot_spacing_y / 2),
        (cradle_center_x + cradle_slot_spacing_x / 2, cradle_center_y + cradle_slot_spacing_y / 2),
    ]
    for sx, sy in cradle_slot_positions:
        with BuildSketch(Plane.XY) as _slot_sk:
            with Locations([(sx, sy)]):
                SlotOverall(slot_length, slot_width)
        extrude(amount=base_thickness, mode=Mode.SUBTRACT)

    # --- Spool holder mounting ---
    # Central hole for spindle plus M3 clearance holes around it.
    spool_spindle_hole = 25.0  # matches spool_spindle_od + clearance
    with Locations([(spool_x, spool_y, 0)]):
        Cylinder(
            radius=spool_spindle_hole / 2,
            height=base_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

    # --- Dancer arm pivot post ---
    # Vertical post rising from the base plate top surface.
    with Locations([(dancer_x, dancer_y, base_thickness)]):
        Cylinder(
            radius=pivot_post_od / 2,
            height=pivot_post_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    # Reinforcement at base of pivot post (wider cylinder, short).
    with Locations([(dancer_x, dancer_y, base_thickness)]):
        Cylinder(
            radius=pivot_post_od / 2 + 3.0,
            height=6.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # --- Guide roller bracket mounting holes ---
    for x_off in [-guide_mount_spacing / 2, guide_mount_spacing / 2]:
        with Locations([(guide_x + x_off, guide_y, 0)]):
            Cylinder(
                radius=m3_hole / 2,
                height=base_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    # --- Corner mounting holes for securing frame to a surface ---
    corner_inset = 8.0
    corner_positions = [
        (-base_length / 2 + corner_inset, -base_width / 2 + corner_inset),
        (base_length / 2 - corner_inset, -base_width / 2 + corner_inset),
        (-base_length / 2 + corner_inset, base_width / 2 - corner_inset),
        (base_length / 2 - corner_inset, base_width / 2 - corner_inset),
    ]
    for cx, cy in corner_positions:
        with Locations([(cx, cy, 0)]):
            Cylinder(
                radius=m3_hole / 2,
                height=base_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    # --- Fillets ---
    # Apply conservatively: base plate top edges and wall-to-base junctions.
    try:
        # Fillet base plate top perimeter edges (the 4 edges at Z=base_thickness
        # that form the outer rectangle).
        base_top_edges = (
            frame.edges()
            .filter_by(Axis.Z, reverse=True)  # non-vertical edges
            .filter_by(lambda e: abs(e.center().Z - base_thickness) < 0.5)
        )
        if base_top_edges:
            fillet(base_top_edges, radius=fillet_radius)
    except Exception:
        print("Warning: base top edge fillets skipped")

    try:
        # Fillet the pivot post base junction
        post_base_edges = (
            frame.edges()
            .filter_by(lambda e: (
                abs(e.center().Z - base_thickness) < 1.0
                and abs(e.center().X - dancer_x) < (pivot_post_od / 2 + 5)
                and abs(e.center().Y - dancer_y) < (pivot_post_od / 2 + 5)
            ))
        )
        if post_base_edges:
            fillet(post_base_edges, radius=fillet_radius)
    except Exception:
        print("Warning: pivot post fillets skipped")

# ---------------------------------------------------------------------------
# Export frame
# ---------------------------------------------------------------------------
result = frame.part
bb = result.bounding_box()
print(f"Main frame bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")

stl_path = str(output_dir / "main_frame.stl")
export_stl(result, stl_path, tolerance=0.01, angular_tolerance=0.1)
print(f"Exported: {stl_path}")

mf_path = str(output_dir / "main_frame.3mf")
try:
    exporter = Mesher()
    exporter.add_shape(result)
    exporter.write(mf_path)
    print(f"Exported: {mf_path}")
except Exception as e:
    try:
        cleaned = result.clean()
        exporter = Mesher()
        exporter.add_shape(cleaned)
        exporter.write(mf_path)
        print(f"Exported (cleaned): {mf_path}")
    except Exception as e2:
        print(f"3mf export failed ({e2}), skipping {mf_path}")

# ---------------------------------------------------------------------------
# Assembly visualization - placeholder shapes at correct positions
# ---------------------------------------------------------------------------
print("\nBuilding assembly visualization...")

with BuildPart() as assembly:
    # Frame (copy)
    add(result)

    # Peel plate placeholder: 46x25x15mm, mounted on the wall
    peel_x = peel_wall_x - 25.0 / 2 - wall_thickness / 2
    peel_z = peel_mount_z
    with Locations([(peel_x, peel_wall_y, peel_z - 7.5)]):
        Box(
            25.0, 46.0, 15.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Vial cradle placeholder: 53x36x23mm
    with Locations([(cradle_center_x, cradle_center_y, base_thickness)]):
        Box(
            53.0, 36.0, 23.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Spool holder placeholder: 40mm flange + spindle
    with Locations([(spool_x, spool_y, base_thickness)]):
        Cylinder(
            radius=20.0,  # 40mm flange diameter / 2
            height=3.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    with Locations([(spool_x, spool_y, base_thickness + 3.0)]):
        Cylinder(
            radius=12.25,
            height=30.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Dancer arm placeholder: flat bar from pivot
    with Locations([(dancer_x, dancer_y, base_thickness + pivot_post_height)]):
        Box(
            60.0, 12.0, 5.0,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    # Guide roller bracket placeholder: 25x20x25mm
    with Locations([(guide_x, guide_y, base_thickness)]):
        Box(
            25.0, 20.0, 25.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

assembly_result = assembly.part
abb = assembly_result.bounding_box()
print(f"Assembly bounding box: {abb.size.X:.2f} x {abb.size.Y:.2f} x {abb.size.Z:.2f} mm")

assembly_stl = str(assembly_dir / "full_assembly.stl")
export_stl(assembly_result, assembly_stl, tolerance=0.01, angular_tolerance=0.1)
print(f"Exported: {assembly_stl}")

print("\nFrame and assembly build complete.")
