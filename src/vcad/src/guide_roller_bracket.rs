//! Guide roller bracket — simplified CSG version.
//!
//! The Build123d version uses an L-shaped bracket with a roller pin hole.
//! This vcad version approximates the shape with box primitives.

use vcad::*;

use crate::config::Config;

pub fn build(cfg: &Config) -> Part {
    let mount_hole_spacing = 15.0;

    // Horizontal base plate
    let base = centered_cube("base", cfg.bracket_base_width, cfg.bracket_base_depth, cfg.wall_thickness);

    // Vertical wall (L-shape)
    let wall = centered_cube("wall", cfg.bracket_base_width, cfg.wall_thickness, cfg.bracket_height)
        .translate(0.0, -cfg.bracket_base_depth / 2.0 + cfg.wall_thickness / 2.0, cfg.wall_thickness / 2.0 + cfg.bracket_height / 2.0);

    // Roller pin hole through vertical wall
    let hole_z = cfg.wall_thickness + cfg.bracket_height - cfg.bearing_od / 2.0 - 2.0;
    let pin_hole = centered_cylinder("pin_hole", cfg.pivot_bore / 2.0, cfg.wall_thickness + 2.0, 32)
        .rotate(90.0, 0.0, 0.0)
        .translate(0.0, -cfg.bracket_base_depth / 2.0 + cfg.wall_thickness / 2.0, hole_z);

    // Two M3 mounting holes in base
    let mount_hole = centered_cylinder("mount_hole", cfg.mount_hole_diameter / 2.0, cfg.wall_thickness + 2.0, 32);
    let mount_holes = mount_hole
        .linear_pattern(mount_hole_spacing, 0.0, 0.0, 2)
        .translate(-mount_hole_spacing / 2.0, 0.0, 0.0);

    (base + wall) - pin_hole - mount_holes
}
