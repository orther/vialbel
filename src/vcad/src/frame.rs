//! Main frame — simplified CSG version.
//!
//! Base plate with mounting wall, adjustment slots (approximated as holes),
//! pivot post, and mounting holes.

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    let pivot_post_od = cfg.pivot_bore;
    let m3_hole = cfg.mount_hole_diameter;

    // Component positions (origin at base plate center)
    let peel_wall_x = cfg.frame_length / 2.0 - cfg.frame_wall_thickness / 2.0 - 5.0;
    let cradle_center_x = peel_wall_x - 35.0;
    let cradle_center_y = 25.0;
    let spool_x = -cfg.frame_length / 2.0 + 30.0;
    let spool_y = -cfg.frame_width / 2.0 + 30.0;
    let dancer_x = -cfg.frame_length / 2.0 + 80.0;
    let dancer_y = -cfg.frame_width / 2.0 + 35.0;
    let guide_x = peel_wall_x - 70.0;
    let guide_y = -cfg.frame_width / 2.0 + 25.0;

    // Base plate
    let base = centered_cube("base", cfg.frame_length, cfg.frame_width, cfg.base_thickness);

    // Peel plate mounting wall
    let wall = centered_cube("wall", cfg.frame_wall_thickness, cfg.frame_width * 0.5, cfg.frame_wall_height)
        .translate(peel_wall_x, 0.0, cfg.base_thickness / 2.0 + cfg.frame_wall_height / 2.0);

    // Dancer arm pivot post
    let post = centered_cylinder("post", pivot_post_od / 2.0, cfg.pivot_post_height, 32)
        .translate(dancer_x, dancer_y, cfg.base_thickness / 2.0 + cfg.pivot_post_height / 2.0);

    // Reinforcement at post base
    let reinforce = centered_cylinder("reinforce", pivot_post_od / 2.0 + 3.0, 6.0, 32)
        .translate(dancer_x, dancer_y, cfg.base_thickness / 2.0 + 3.0);

    // Spool spindle hole
    let spool_hole = centered_cylinder("spool_hole", 12.5, cfg.base_thickness + 2.0, 32)
        .translate(spool_x, spool_y, 0.0);

    // Guide roller bracket mounting holes
    let guide_hole = centered_cylinder("guide_hole", m3_hole / 2.0, cfg.base_thickness + 2.0, 32);
    let guide_holes = guide_hole
        .linear_pattern(15.0, 0.0, 0.0, 2)
        .translate(guide_x - 7.5, guide_y, 0.0);

    // Corner mounting holes
    let corner_hole = centered_cylinder("corner", m3_hole / 2.0, cfg.base_thickness + 2.0, 32);
    let inset = 8.0;
    let c1 = corner_hole.translate(-cfg.frame_length / 2.0 + inset, -cfg.frame_width / 2.0 + inset, 0.0);
    let c2 = corner_hole.translate(cfg.frame_length / 2.0 - inset, -cfg.frame_width / 2.0 + inset, 0.0);
    let c3 = corner_hole.translate(-cfg.frame_length / 2.0 + inset, cfg.frame_width / 2.0 - inset, 0.0);
    let c4 = corner_hole.translate(cfg.frame_length / 2.0 - inset, cfg.frame_width / 2.0 - inset, 0.0);

    // Cradle mounting holes (simplified from slots to round holes)
    let cradle_hole = centered_cylinder("cradle_hole", m3_hole / 2.0, cfg.base_thickness + 2.0, 32);
    let sx = cfg.cradle_mount_slot_spacing_x / 2.0;
    let sy = cfg.cradle_mount_slot_spacing_y / 2.0;
    let ch1 = cradle_hole.translate(cradle_center_x - sx, cradle_center_y - sy, 0.0);
    let ch2 = cradle_hole.translate(cradle_center_x + sx, cradle_center_y - sy, 0.0);
    let ch3 = cradle_hole.translate(cradle_center_x - sx, cradle_center_y + sy, 0.0);
    let ch4 = cradle_hole.translate(cradle_center_x + sx, cradle_center_y + sy, 0.0);

    (base + wall + post + reinforce)
        - spool_hole
        - guide_holes
        - c1 - c2 - c3 - c4
        - ch1 - ch2 - ch3 - ch4
}
