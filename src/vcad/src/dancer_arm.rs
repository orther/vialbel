//! Dancer arm — simplified CSG version.
//!
//! The Build123d version uses a 2D sketch with hub circles and extrusion.
//! This vcad version approximates the shape with box and cylinder primitives.

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    let pivot_hub_radius = cfg.pivot_bore / 2.0 + cfg.wall_thickness + 2.0;
    let roller_hub_radius = cfg.bearing_od / 2.0 + cfg.wall_thickness;

    // Pivot hub cylinder
    let pivot_hub = centered_cylinder("pivot_hub", pivot_hub_radius, cfg.dancer_arm_thickness, 64);

    // Roller hub cylinder at far end
    let roller_hub = centered_cylinder("roller_hub", roller_hub_radius, cfg.dancer_arm_thickness, 64)
        .translate(cfg.dancer_arm_length, 0.0, 0.0);

    // Connecting bar
    let bar = centered_cube("bar", cfg.dancer_arm_length, cfg.dancer_arm_width, cfg.dancer_arm_thickness)
        .translate(cfg.dancer_arm_length / 2.0, 0.0, 0.0);

    // Pivot bore
    let pivot_hole = centered_cylinder("pivot_hole", cfg.pivot_bore / 2.0, cfg.dancer_arm_thickness + 2.0, 32);

    // Bearing bore at roller end
    let bearing_hole = centered_cylinder("bearing_hole", cfg.bearing_id / 2.0, cfg.dancer_arm_thickness + 2.0, 32)
        .translate(cfg.dancer_arm_length, 0.0, 0.0);

    // Spring attachment hole
    let spring_hole = centered_cylinder("spring_hole", 1.5, cfg.dancer_arm_thickness + 2.0, 32)
        .translate(10.0, cfg.dancer_arm_width / 2.0 - 1.5, 0.0);

    (pivot_hub + roller_hub + bar) - pivot_hole - bearing_hole - spring_hole
}
