//! Main frame — simplified CSG version.
//!
//! Base plate with mounting wall, adjustment slots (approximated as holes),
//! pivot post, and mounting holes.

use vcad::*;

// Parameters (matching src/frame.py)
const BASE_LENGTH: f64 = 200.0;
const BASE_WIDTH: f64 = 120.0;
const BASE_THICKNESS: f64 = 5.0;
const WALL_HEIGHT: f64 = 30.0;
const WALL_THICKNESS: f64 = 4.0;
const PIVOT_POST_OD: f64 = 8.0;
const PIVOT_POST_HEIGHT: f64 = 40.0;
const M3_HOLE: f64 = 3.2;

// Component positions (origin at base plate center)
const PEEL_WALL_X: f64 = BASE_LENGTH / 2.0 - WALL_THICKNESS / 2.0 - 5.0;
const CRADLE_CENTER_X: f64 = PEEL_WALL_X - 35.0;
const CRADLE_CENTER_Y: f64 = 25.0;
const SPOOL_X: f64 = -BASE_LENGTH / 2.0 + 30.0;
const SPOOL_Y: f64 = -BASE_WIDTH / 2.0 + 30.0;
const DANCER_X: f64 = -BASE_LENGTH / 2.0 + 80.0;
const DANCER_Y: f64 = -BASE_WIDTH / 2.0 + 35.0;
const GUIDE_X: f64 = PEEL_WALL_X - 70.0;
const GUIDE_Y: f64 = -BASE_WIDTH / 2.0 + 25.0;

pub fn build() -> Part {
    // Base plate
    let base = centered_cube("base", BASE_LENGTH, BASE_WIDTH, BASE_THICKNESS);

    // Peel plate mounting wall
    let wall = centered_cube("wall", WALL_THICKNESS, BASE_WIDTH * 0.5, WALL_HEIGHT)
        .translate(PEEL_WALL_X, 0.0, BASE_THICKNESS / 2.0 + WALL_HEIGHT / 2.0);

    // Dancer arm pivot post
    let post = centered_cylinder("post", PIVOT_POST_OD / 2.0, PIVOT_POST_HEIGHT, 32)
        .translate(DANCER_X, DANCER_Y, BASE_THICKNESS / 2.0 + PIVOT_POST_HEIGHT / 2.0);

    // Reinforcement at post base
    let reinforce = centered_cylinder("reinforce", PIVOT_POST_OD / 2.0 + 3.0, 6.0, 32)
        .translate(DANCER_X, DANCER_Y, BASE_THICKNESS / 2.0 + 3.0);

    // Spool spindle hole
    let spool_hole = centered_cylinder("spool_hole", 12.5, BASE_THICKNESS + 2.0, 32)
        .translate(SPOOL_X, SPOOL_Y, 0.0);

    // Guide roller bracket mounting holes
    let guide_hole = centered_cylinder("guide_hole", M3_HOLE / 2.0, BASE_THICKNESS + 2.0, 32);
    let guide_holes = guide_hole
        .linear_pattern(15.0, 0.0, 0.0, 2)
        .translate(GUIDE_X - 7.5, GUIDE_Y, 0.0);

    // Corner mounting holes
    let corner_hole = centered_cylinder("corner", M3_HOLE / 2.0, BASE_THICKNESS + 2.0, 32);
    let inset = 8.0;
    let c1 = corner_hole.translate(-BASE_LENGTH / 2.0 + inset, -BASE_WIDTH / 2.0 + inset, 0.0);
    let c2 = corner_hole.translate(BASE_LENGTH / 2.0 - inset, -BASE_WIDTH / 2.0 + inset, 0.0);
    let c3 = corner_hole.translate(-BASE_LENGTH / 2.0 + inset, BASE_WIDTH / 2.0 - inset, 0.0);
    let c4 = corner_hole.translate(BASE_LENGTH / 2.0 - inset, BASE_WIDTH / 2.0 - inset, 0.0);

    // Cradle mounting holes (simplified from slots to round holes)
    let cradle_hole = centered_cylinder("cradle_hole", M3_HOLE / 2.0, BASE_THICKNESS + 2.0, 32);
    let sx = 36.0 / 2.0;
    let sy = 20.0 / 2.0;
    let ch1 = cradle_hole.translate(CRADLE_CENTER_X - sx, CRADLE_CENTER_Y - sy, 0.0);
    let ch2 = cradle_hole.translate(CRADLE_CENTER_X + sx, CRADLE_CENTER_Y - sy, 0.0);
    let ch3 = cradle_hole.translate(CRADLE_CENTER_X - sx, CRADLE_CENTER_Y + sy, 0.0);
    let ch4 = cradle_hole.translate(CRADLE_CENTER_X + sx, CRADLE_CENTER_Y + sy, 0.0);

    (base + wall + post + reinforce)
        - spool_hole
        - guide_holes
        - c1 - c2 - c3 - c4
        - ch1 - ch2 - ch3 - ch4
}
