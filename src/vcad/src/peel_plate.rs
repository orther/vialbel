//! Peel plate — simplified CSG version.
//!
//! The Build123d version uses a complex wedge profile with BREP fillets.
//! This vcad version approximates the shape with box primitives and
//! boolean operations. No fillets (mesh-based geometry).

use vcad::*;

// Parameters (matching src/peel_plate.py)
const LABEL_WIDTH: f64 = 40.0;
const BODY_DEPTH: f64 = 25.0;
const BODY_HEIGHT_REAR: f64 = 15.0;
const CHANNEL_WIDTH: f64 = LABEL_WIDTH + 1.0; // 41mm
const CHANNEL_DEPTH: f64 = 1.5;
const WALL_THICKNESS: f64 = 2.5;
const MOUNT_HOLE_DIAMETER: f64 = 3.2;
const MOUNT_HOLE_SPACING: f64 = 30.0;

pub fn build() -> Part {
    // Main body — rectangular block (the wedge shape is approximated as a box
    // since vcad doesn't have native wedge/loft operations).
    let body = centered_cube("body", LABEL_WIDTH + 2.0 * WALL_THICKNESS, BODY_DEPTH, BODY_HEIGHT_REAR);

    // Channel cut — slot along the top for the label path.
    let channel = centered_cube("channel", CHANNEL_WIDTH, BODY_DEPTH + 2.0, CHANNEL_DEPTH)
        .translate(0.0, 0.0, BODY_HEIGHT_REAR / 2.0 - CHANNEL_DEPTH / 2.0);

    // Mounting holes — two M3 clearance holes on the rear face.
    let hole = centered_cylinder("hole", MOUNT_HOLE_DIAMETER / 2.0, BODY_DEPTH + 2.0, 32);
    let holes = hole
        .translate(0.0, 0.0, 0.0)
        .linear_pattern(MOUNT_HOLE_SPACING, 0.0, 0.0, 2)
        .translate(-MOUNT_HOLE_SPACING / 2.0, 0.0, 0.0);

    body - channel - holes
}
