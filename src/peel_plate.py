"""Peel plate for thermal label separation from backing paper.

The peel plate uses a sharp-angled edge with a small radius fillet to
separate thermal labels from their backing paper. The backing paper enters
from the top, passes over the peel edge, and reverses 180 degrees to exit
downward. The peeled label presents flat on the top surface for vial contact.
"""

from build123d import *

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
label_width = 40.0  # mm - width of thermal label
label_clearance = 0.5  # mm - clearance per side between label and guide rail
peel_radius = 2.0  # mm - radius of the peel edge fillet
guide_rail_height = 3.0  # mm - height of side rails above label path surface
wall_thickness = 2.5  # mm - thickness of side walls / guide rails
mount_hole_diameter = 3.2  # mm - M3 clearance hole
mount_hole_spacing = 30.0  # mm - distance between mounting holes

# ---------------------------------------------------------------------------
# Derived dimensions
# ---------------------------------------------------------------------------
internal_width = label_width + 2 * label_clearance  # 41mm channel for label
overall_width = internal_width + 2 * wall_thickness  # total width with walls
overall_depth = 25.0  # mm - front to back
overall_height = 15.0  # mm - total height of wedge body
wedge_front_height = 4.0  # mm - thin front edge before fillet
top_surface_depth = 18.0  # mm - flat top where label presents
mount_tab_depth = 8.0  # mm - depth of rear section with mount holes
mount_hole_y = overall_height / 2  # vertical center of mount holes

# ---------------------------------------------------------------------------
# Build the peel plate
# ---------------------------------------------------------------------------
with BuildPart() as part:
    # Main wedge body: a loft from tall rear face to short front edge.
    # We build this as a Box for the base, then cut the wedge angle.
    #
    # Coordinate system:
    #   X = width (label travels perpendicular)
    #   Y = depth (front-to-back, front is +Y)
    #   Z = height (up)
    #
    # Strategy: create a prismatic wedge using a sketch extruded along X.

    # --- Base wedge shape (side profile extruded across width) ---
    with BuildSketch(Plane.YZ) as wedge_profile:
        with BuildLine():
            # Start at rear-bottom
            l1 = Line((0, 0), (overall_depth, 0))  # bottom face, rear to front
            l2 = Line(l1 @ 1, (overall_depth, wedge_front_height))  # front face up
            l3 = Line(l2 @ 1, (overall_depth - top_surface_depth, overall_height))  # angled top to flat
            l4 = Line(l3 @ 1, (0, overall_height))  # flat top / rear top
            l5 = Line(l4 @ 1, l1 @ 0)  # rear face down
        make_face()

    extrude(amount=overall_width, both=False)

    # Center the part on X axis
    with Locations((0, 0, 0)):
        pass  # already centered via next step

    # The extrusion went in +X from YZ plane. Re-center on X.
    # Move so X is centered: shift by -overall_width/2
    # Actually, let's just work with the geometry as-is and adjust later.

    # --- Cut the internal channel (label path) from the top ---
    # The channel removes material between the guide rails on the top surface.
    # We cut from the top, leaving the guide rails on each side.
    with BuildSketch(part.faces().sort_by(Axis.Z)[-1]) as channel_cut:
        # Top face - cut a rectangle for the label channel
        # The top face is at Z = overall_height, spans X and Y
        # We want to remove material in the center, leaving wall_thickness on each side
        with Locations((overall_width / 2, 0)):
            Rectangle(internal_width, overall_depth + 1)

    extrude(amount=-guide_rail_height, mode=Mode.SUBTRACT)

    # --- Fillet the front peel edge ---
    # The peel edge is the front-top edge where the wedge meets the top.
    # Select edges at the front (max Y) that are along X direction.
    front_top_edges = (
        part.edges()
        .filter_by(Axis.X)
        .sort_by(Axis.Y)[-3:]  # front-most X-parallel edges
    )
    # Filter to only those near the top
    peel_edges = []
    for e in front_top_edges:
        center = e.center()
        if center.Z > wedge_front_height * 0.5:
            peel_edges.append(e)

    if peel_edges:
        try:
            fillet(peel_edges, radius=peel_radius)
        except Exception:
            # If fillet fails on multiple edges, try just the topmost front edge
            top_front = part.edges().filter_by(Axis.X).sort_by(Axis.Y)[-1]
            try:
                fillet([top_front], radius=peel_radius)
            except Exception:
                print("Warning: peel edge fillet could not be applied")

    # --- Mounting holes on the rear face ---
    # Rear face is at Y=0 (minimum Y). Holes go into the part along +Y.
    rear_face = part.faces().sort_by(Axis.Y)[0]
    with BuildSketch(rear_face) as mount_sketch:
        with Locations(
            (-mount_hole_spacing / 2 + overall_width / 2, mount_hole_y),
            (mount_hole_spacing / 2 + overall_width / 2, mount_hole_y),
        ):
            Circle(mount_hole_diameter / 2)

    extrude(amount=-mount_tab_depth, mode=Mode.SUBTRACT)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
result = part.part
bb = result.bounding_box()
print(f"Peel plate bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")

export_stl(result, "models/components/peel_plate.stl", tolerance=0.01, angular_tolerance=0.1)
print("Exported: models/components/peel_plate.stl")

exporter = Mesher()
exporter.add_shape(result)
exporter.write("models/components/peel_plate.3mf")
print("Exported: models/components/peel_plate.3mf")

print("Peel plate build complete.")
