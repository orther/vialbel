//! Dancer arm — simplified CSG version.
//!
//! The Build123d version uses a 2D sketch with hub circles and extrusion.
//! This vcad version approximates the shape with box and cylinder primitives.

use vcad::*;

// Parameters (matching src/tension_system.py)
const ARM_LENGTH: f64 = 60.0;
const ARM_WIDTH: f64 = 12.0;
const ARM_THICKNESS: f64 = 5.0;
const PIVOT_BORE: f64 = 8.0;
const BEARING_ID: f64 = 8.0;
const BEARING_OD: f64 = 22.0;
const WALL_THICKNESS: f64 = 2.5;

pub fn build() -> Part {
    let pivot_hub_radius = PIVOT_BORE / 2.0 + WALL_THICKNESS + 2.0;
    let roller_hub_radius = BEARING_OD / 2.0 + WALL_THICKNESS;

    // Pivot hub cylinder
    let pivot_hub = centered_cylinder("pivot_hub", pivot_hub_radius, ARM_THICKNESS, 64);

    // Roller hub cylinder at far end
    let roller_hub = centered_cylinder("roller_hub", roller_hub_radius, ARM_THICKNESS, 64)
        .translate(ARM_LENGTH, 0.0, 0.0);

    // Connecting bar
    let bar = centered_cube("bar", ARM_LENGTH, ARM_WIDTH, ARM_THICKNESS)
        .translate(ARM_LENGTH / 2.0, 0.0, 0.0);

    // Pivot bore
    let pivot_hole = centered_cylinder("pivot_hole", PIVOT_BORE / 2.0, ARM_THICKNESS + 2.0, 32);

    // Bearing bore at roller end
    let bearing_hole = centered_cylinder("bearing_hole", BEARING_ID / 2.0, ARM_THICKNESS + 2.0, 32)
        .translate(ARM_LENGTH, 0.0, 0.0);

    // Spring attachment hole
    let spring_hole = centered_cylinder("spring_hole", 1.5, ARM_THICKNESS + 2.0, 32)
        .translate(10.0, ARM_WIDTH / 2.0 - 1.5, 0.0);

    (pivot_hub + roller_hub + bar) - pivot_hole - bearing_hole - spring_hole
}
