"""Mechanical constants for vial label applicator animation."""

# Coordinate system: X left(-)/right(+), Y back(-)/front(+), Z bottom(0)/top(+)
# All values in millimeters

# Key positions (mm)
SPOOL_EXIT = (-70.0, -30.0, 23.0)
DANCER_ROLLER_CENTER = (-20.0, -15.0, 47.5)
GUIDE_ROLLER_CENTER = (23.0, -35.0, 17.0)
PEEL_ENTRY = (68.0, 0.0, 25.0)
PEEL_EDGE = (80.5, 0.0, 20.0)
VIAL_CENTER = (58.0, 25.0, 16.31)

# Radii
DANCER_ROLLER_RADIUS = 11.0
GUIDE_ROLLER_RADIUS = 11.0
PEEL_RADIUS = 2.0
VIAL_RADIUS = 8.0

# Label
LABEL_WIDTH = 40.0  # mm
LABEL_HEIGHT = 20.0  # mm
LABEL_THICKNESS = 0.15  # mm
LABEL_WRAP_ANGLE = 270.0  # degrees

# Dancer
DANCER_PIVOT = (-20.0, -25.0, 45.0)

# Backing paper
BACKING_WRAP_ANGLE = 160.0  # degrees around peel radius
