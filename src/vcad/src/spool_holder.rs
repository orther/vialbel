//! Spool holder — simplified CSG version.
//!
//! The Build123d version uses precise cylinders with mounting holes.
//! This vcad version approximates the shape with cylinder primitives
//! and boolean operations.

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    // Base flange
    let flange = centered_cylinder("flange", cfg.spool_flange_diameter / 2.0, cfg.spool_flange_thickness, 64);

    // Spindle on top of flange
    let spindle = centered_cylinder("spindle", cfg.spool_spindle_od / 2.0, cfg.spool_height, 64)
        .translate(0.0, 0.0, (cfg.spool_flange_thickness + cfg.spool_height) / 2.0);

    // M3 mounting hole through center
    let hole = centered_cylinder("hole", cfg.mount_hole_diameter / 2.0, cfg.spool_flange_thickness + 2.0, 32);

    (flange + spindle) - hole
}
