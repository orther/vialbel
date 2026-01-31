//! Peel plate — simplified CSG version.
//!
//! The Build123d version uses a complex wedge profile with BREP fillets.
//! This vcad version approximates the shape with box primitives and
//! boolean operations. No fillets (mesh-based geometry).

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    let channel_width = cfg.label_width + cfg.peel_channel_width_clearance;
    let body_width = cfg.label_width + 2.0 * cfg.wall_thickness;

    // Main body — rectangular block (the wedge shape is approximated as a box
    // since vcad doesn't have native wedge/loft operations).
    let body = centered_cube("body", body_width, cfg.peel_body_depth, cfg.peel_body_height_rear);

    // Channel cut — slot along the top for the label path.
    let channel_depth = 1.5;
    let channel = centered_cube("channel", channel_width, cfg.peel_body_depth + 2.0, channel_depth)
        .translate(0.0, 0.0, cfg.peel_body_height_rear / 2.0 - channel_depth / 2.0);

    // Mounting holes — two M3 clearance holes on the rear face.
    let hole = centered_cylinder("hole", cfg.mount_hole_diameter / 2.0, cfg.peel_body_depth + 2.0, 32);
    let holes = hole
        .translate(0.0, 0.0, 0.0)
        .linear_pattern(cfg.peel_mount_hole_spacing, 0.0, 0.0, 2)
        .translate(-cfg.peel_mount_hole_spacing / 2.0, 0.0, 0.0);

    body - channel - holes
}
