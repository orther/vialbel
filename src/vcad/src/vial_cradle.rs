//! Vial cradle — simplified CSG version.
//!
//! The Build123d version uses a precise V-block with trigonometric calculations.
//! This vcad version approximates the V-groove using two angled box cuts.

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    let cradle_length = cfg.vial_height - 3.5; // match Python: vial_height - small clearance
    let base_width = cfg.vial_diameter + 20.0;
    let m3_hole = 3.4;

    // Base plate
    let base = centered_cube("base", cradle_length + 18.0, base_width, cfg.cradle_base_height);

    // V-block body — tall block that will be cut to form the V
    let v_body = centered_cube("v_body", cradle_length, base_width, cfg.cradle_v_block_height)
        .translate(0.0, 0.0, cfg.cradle_base_height / 2.0 + cfg.cradle_v_block_height / 2.0);

    // V-groove cut — approximate with two angled boxes rotated 45 degrees.
    let cut_size = cfg.vial_diameter * 1.5;
    let cut_block = centered_cube("cut", cradle_length + 2.0, cut_size, cut_size)
        .rotate(45.0, 0.0, 0.0)
        .translate(0.0, 0.0, cfg.cradle_base_height + cfg.cradle_v_block_height - cut_size * 0.35);

    // Mounting holes — 4 holes at corners of the base
    let hole = centered_cylinder("hole", m3_hole / 2.0, cfg.cradle_base_height + 2.0, 32);
    let holes = hole
        .linear_pattern(cfg.cradle_mount_slot_spacing_x, 0.0, 0.0, 2)
        .linear_pattern(0.0, cfg.cradle_mount_slot_spacing_y, 0.0, 2)
        .translate(
            -cfg.cradle_mount_slot_spacing_x / 2.0,
            -cfg.cradle_mount_slot_spacing_y / 2.0,
            0.0,
        );

    (base + v_body) - cut_block - holes
}
