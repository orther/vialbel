//! Vial cradle — simplified CSG version.
//!
//! The Build123d version uses a precise V-block with trigonometric calculations.
//! This vcad version approximates the V-groove using two angled box cuts.

use vcad::*;

// Parameters (matching src/vial_cradle.py)
const VIAL_DIAMETER: f64 = 16.0;
const CRADLE_LENGTH: f64 = 35.0;
const BASE_WIDTH: f64 = VIAL_DIAMETER + 20.0;  // 36mm
const BASE_HEIGHT: f64 = 5.0;
const V_BLOCK_HEIGHT: f64 = 18.0;  // total height above base
const MOUNT_SLOT_SPACING_X: f64 = 36.0;
const MOUNT_SLOT_SPACING_Y: f64 = 20.0;
const M3_HOLE: f64 = 3.4;

pub fn build() -> Part {
    // Base plate
    let base = centered_cube("base", CRADLE_LENGTH + 18.0, BASE_WIDTH, BASE_HEIGHT);

    // V-block body — tall block that will be cut to form the V
    let v_body = centered_cube("v_body", CRADLE_LENGTH, BASE_WIDTH, V_BLOCK_HEIGHT)
        .translate(0.0, 0.0, BASE_HEIGHT / 2.0 + V_BLOCK_HEIGHT / 2.0);

    // V-groove cut — approximate with two angled boxes rotated 45 degrees.
    // A 90-degree V-groove for a 16mm vial.
    let cut_size = VIAL_DIAMETER * 1.5;
    let cut_block = centered_cube("cut", CRADLE_LENGTH + 2.0, cut_size, cut_size)
        .rotate(45.0, 0.0, 0.0)
        .translate(0.0, 0.0, BASE_HEIGHT + V_BLOCK_HEIGHT - cut_size * 0.35);

    // Mounting holes — 4 holes at corners of the base
    let hole = centered_cylinder("hole", M3_HOLE / 2.0, BASE_HEIGHT + 2.0, 32);
    let holes = hole
        .linear_pattern(MOUNT_SLOT_SPACING_X, 0.0, 0.0, 2)
        .linear_pattern(0.0, MOUNT_SLOT_SPACING_Y, 0.0, 2)
        .translate(
            -MOUNT_SLOT_SPACING_X / 2.0,
            -MOUNT_SLOT_SPACING_Y / 2.0,
            0.0,
        );

    (base + v_body) - cut_block - holes
}
