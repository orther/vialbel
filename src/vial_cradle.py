"""Vial cradle/holder for label application.

A V-block cradle that holds a 16mm cylindrical vial during label rolling.
The vial rotates freely while a label is applied by rolling contact.
"""

import math
from build123d import *

from config import load_config

cfg = load_config()

# --- Parameters ---
vial_diameter = cfg["vial_diameter"]
vial_radius = vial_diameter / 2.0
vial_height = cfg["vial_height"]
label_bottom_offset = cfg["label_offset_from_bottom"]
label_height = cfg["label_height"]
v_angle = 90.0  # included angle of V-block
wall_thickness = cfg["wall_thickness"]
base_thickness = cfg["base_thickness"]
cradle_length = cfg["cradle_length"]
mount_slot_length = 5.0
mount_slot_width = cfg["mount_hole_diameter"]  # for M3 bolts

# --- Derived dimensions ---
half_angle = math.radians(v_angle / 2.0)  # 45 degrees

# Distance from V vertex to vial center = r / sin(half_angle)
center_above_vertex = vial_radius / math.sin(half_angle)  # ~11.31mm

# The V-block walls need to be tall enough that the vial doesn't fall out.
# Vial center above vertex is ~11.31mm. Vial top edge is at 11.31 + 8 = 19.31mm above vertex.
# Walls should reach at least to vial center height.
v_wall_height = center_above_vertex + vial_radius * 0.5  # ~15.3mm above vertex

# Width of V opening at the top of the walls
v_top_half_width = v_wall_height * math.tan(half_angle)  # at 45deg, equals v_wall_height
v_top_width = 2.0 * v_top_half_width

# Overall block width: V opening + wall thickness on each side
block_width = v_top_width + 2.0 * wall_thickness

# The V vertex sits inside the base. Place vertex at base_thickness height from bottom
# so the V groove is cut into the block.
vertex_z = base_thickness  # vertex at top of base plate

# Total block height: base + wall height above vertex
block_height = base_thickness + v_wall_height

# Height stop wall thickness and position
stop_wall_thickness = 3.0

# Base plate extends beyond cradle for mounting
base_length = cradle_length + stop_wall_thickness + 15.0  # extra length for slots
base_width = block_width

print(f"Vial radius: {vial_radius:.2f} mm")
print(f"Center above V vertex: {center_above_vertex:.2f} mm")
print(f"V wall height above vertex: {v_wall_height:.2f} mm")
print(f"Block width: {block_width:.2f} mm")
print(f"Block height: {block_height:.2f} mm")
print(f"Base length: {base_length:.2f} mm")

# --- Build the cradle ---
with BuildPart() as cradle:
    # Base plate - full length, centered at origin
    with BuildSketch(Plane.XY) as base_sk:
        Rectangle(base_length, base_width)
    extrude(amount=base_thickness)

    # V-block solid - only cradle_length portion, offset to one end
    # Position: the V-block starts at one end, stop wall is at the back
    v_block_x_center = -base_length / 2.0 + stop_wall_thickness + cradle_length / 2.0

    with BuildSketch(Plane.XY) as vblock_sk:
        with Locations([(v_block_x_center, 0)]):
            Rectangle(cradle_length, block_width)
    extrude(amount=block_height)

    # Height stop wall - at the back end of the V-block
    stop_x_center = -base_length / 2.0 + stop_wall_thickness / 2.0
    with BuildSketch(Plane.XY) as stop_sk:
        with Locations([(stop_x_center, 0)]):
            Rectangle(stop_wall_thickness, block_width)
    extrude(amount=block_height + 5.0)  # taller than V walls

    # Cut the V-groove through the V-block and stop wall
    # The V-groove is along the X axis. We define a cross-section (YZ plane)
    # and extrude along X.
    # V-groove cross section: a triangle pointing down, vertex at z=vertex_z
    # The triangle extends upward and outward at 45 degrees each side.
    # We make it large enough to cut through everything above.
    groove_cut_height = block_height + 10.0  # generous cut height
    groove_half_width_at_top = groove_cut_height * math.tan(half_angle)

    # The groove runs the full length of base (through V-block and stop wall)
    groove_length = base_length + 2.0  # extra to ensure clean cut

    with BuildPart(mode=Mode.SUBTRACT) as groove_cut:
        # Build sketch on YZ plane, then extrude along X
        # Position the sketch at the left end
        sketch_plane = Plane(
            origin=(-groove_length / 2.0, 0, 0),
            x_dir=(0, 1, 0),
            z_dir=(1, 0, 0),
        )
        with BuildSketch(sketch_plane) as groove_sk:
            # Triangle: vertex at (0, vertex_z), expanding upward
            Polygon(
                [
                    (0, vertex_z),  # vertex of V
                    (-groove_half_width_at_top, vertex_z + groove_cut_height),
                    (groove_half_width_at_top, vertex_z + groove_cut_height),
                ],
                align=None,
            )
        extrude(amount=groove_length)

    # Cut mounting slots in the base plate extension area
    # Slots are on the right side of the base (beyond V-block)
    slot_area_start = v_block_x_center + cradle_length / 2.0 + 2.0
    slot_x1 = slot_area_start + mount_slot_length / 2.0
    slot_x2 = slot_x1 + mount_slot_length + 3.0  # second slot

    # Only add slots if they fit within the base
    slot_positions = []
    for sx in [slot_x1, slot_x2]:
        if sx + mount_slot_length / 2.0 < base_length / 2.0:
            slot_positions.append(sx)

    if slot_positions:
        with BuildPart(mode=Mode.SUBTRACT):
            for sx in slot_positions:
                with BuildSketch(Plane.XY) as slot_sk:
                    with Locations([(sx, 0)]):
                        SlotOverall(mount_slot_length, mount_slot_width)
                extrude(amount=base_thickness)

part = cradle.part

# --- Bounding box ---
bb = part.bounding_box()
print(f"\nBounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")

# --- Export ---
stl_path = "models/components/vial_cradle.stl"
threemf_path = "models/components/vial_cradle.3mf"

export_stl(part, stl_path, tolerance=0.01, angular_tolerance=0.1)
print(f"Exported: {stl_path}")

exporter = Mesher()
exporter.add_shape(part)
exporter.write(threemf_path)
print(f"Exported: {threemf_path}")

print("\nVial cradle build complete.")
