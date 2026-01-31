//! Guide roller bracket — simplified CSG version.
//!
//! The Build123d version uses an L-shaped bracket with a roller pin hole.
//! This vcad version approximates the shape with box primitives.

use vcad::*;

// Parameters (matching src/tension_system.py)
const BRACKET_BASE_WIDTH: f64 = 25.0;
const BRACKET_BASE_DEPTH: f64 = 20.0;
const BRACKET_HEIGHT: f64 = 25.0;
const WALL_THICKNESS: f64 = 2.5;
const PIVOT_BORE: f64 = 8.0;
const BEARING_OD: f64 = 22.0;
const MOUNT_HOLE_DIAMETER: f64 = 3.2;
const MOUNT_HOLE_SPACING: f64 = 15.0;

pub fn build() -> Part {
    // Horizontal base plate
    let base = centered_cube("base", BRACKET_BASE_WIDTH, BRACKET_BASE_DEPTH, WALL_THICKNESS);

    // Vertical wall (L-shape)
    let wall = centered_cube("wall", BRACKET_BASE_WIDTH, WALL_THICKNESS, BRACKET_HEIGHT)
        .translate(0.0, -BRACKET_BASE_DEPTH / 2.0 + WALL_THICKNESS / 2.0, WALL_THICKNESS / 2.0 + BRACKET_HEIGHT / 2.0);

    // Roller pin hole through vertical wall
    let hole_z = WALL_THICKNESS + BRACKET_HEIGHT - BEARING_OD / 2.0 - 2.0;
    let pin_hole = centered_cylinder("pin_hole", PIVOT_BORE / 2.0, WALL_THICKNESS + 2.0, 32)
        .rotate(90.0, 0.0, 0.0)
        .translate(0.0, -BRACKET_BASE_DEPTH / 2.0 + WALL_THICKNESS / 2.0, hole_z);

    // Two M3 mounting holes in base
    let mount_hole = centered_cylinder("mount_hole", MOUNT_HOLE_DIAMETER / 2.0, WALL_THICKNESS + 2.0, 32);
    let mount_holes = mount_hole
        .linear_pattern(MOUNT_HOLE_SPACING, 0.0, 0.0, 2)
        .translate(-MOUNT_HOLE_SPACING / 2.0, 0.0, 0.0);

    (base + wall) - pin_hole - mount_holes
}
