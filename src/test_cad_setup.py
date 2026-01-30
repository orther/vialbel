"""Test script to verify Build123d installation and export capabilities."""

from build123d import *

# Parameters
diameter = 16.0  # mm
height = 20.0  # mm
fillet_radius = 2.0  # mm

# Build a simple cylinder with filleted edges (simulates vial shape)
with BuildPart() as test_part:
    Cylinder(radius=diameter / 2, height=height)
    # Fillet top and bottom edges
    fillet(test_part.edges(), radius=fillet_radius)

part = test_part.part

# Export STL
export_stl(part, "models/test/test_cylinder.stl", tolerance=0.01, angular_tolerance=0.1)
print("Exported: models/test/test_cylinder.stl")

# Export 3MF
exporter = Mesher()
exporter.add_shape(part)
exporter.write("models/test/test_cylinder.3mf")
print("Exported: models/test/test_cylinder.3mf")

# Print bounding box to verify dimensions
bb = part.bounding_box()
print(f"Bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
print(f"Expected:     ~{diameter:.2f} x ~{diameter:.2f} x ~{height:.2f} mm")
print("Build123d setup verified successfully.")
