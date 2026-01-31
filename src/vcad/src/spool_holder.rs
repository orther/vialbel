//! Spool holder — simplified CSG version.
//!
//! The Build123d version uses precise cylinders with mounting holes.
//! This vcad version approximates the shape with cylinder primitives
//! and boolean operations.

use vcad::*;

// Parameters (matching src/tension_system.py)
const SPOOL_SPINDLE_OD: f64 = 24.5;
const SPOOL_HEIGHT: f64 = 30.0;
const SPOOL_FLANGE_DIAMETER: f64 = 40.0;
const SPOOL_FLANGE_THICKNESS: f64 = 3.0;
const MOUNT_HOLE_DIAMETER: f64 = 3.2;

pub fn build() -> Part {
    // Base flange
    let flange = centered_cylinder("flange", SPOOL_FLANGE_DIAMETER / 2.0, SPOOL_FLANGE_THICKNESS, 64);

    // Spindle on top of flange
    let spindle = centered_cylinder("spindle", SPOOL_SPINDLE_OD / 2.0, SPOOL_HEIGHT, 64)
        .translate(0.0, 0.0, (SPOOL_FLANGE_THICKNESS + SPOOL_HEIGHT) / 2.0);

    // M3 mounting hole through center
    let hole = centered_cylinder("hole", MOUNT_HOLE_DIAMETER / 2.0, SPOOL_FLANGE_THICKNESS + 2.0, 32);

    (flange + spindle) - hole
}
