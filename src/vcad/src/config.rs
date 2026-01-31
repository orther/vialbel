//! Configuration loader — reads shared parameters from the project root config.toml.

use serde::Deserialize;
use std::path::{Path, PathBuf};

/// All parameters from the `[default]` section of config.toml.
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct Config {
    pub vial_diameter: f64,
    pub vial_height: f64,
    pub label_width: f64,
    pub label_height: f64,
    pub label_offset_from_bottom: f64,
    pub label_thickness: f64,
    pub min_bend_radius: f64,
    pub wall_thickness: f64,
    pub base_thickness: f64,
    pub mount_hole_diameter: f64,
    pub fillet_radius: f64,
    pub frame_length: f64,
    pub frame_width: f64,
    pub frame_wall_height: f64,
    pub frame_wall_thickness: f64,
    pub peel_channel_width_clearance: f64,
    pub peel_body_depth: f64,
    pub peel_body_height_rear: f64,
    pub peel_mount_hole_spacing: f64,
    pub cradle_base_height: f64,
    pub cradle_v_block_height: f64,
    pub cradle_mount_slot_spacing_x: f64,
    pub cradle_mount_slot_spacing_y: f64,
    pub spool_spindle_od: f64,
    pub spool_flange_diameter: f64,
    pub spool_flange_thickness: f64,
    pub spool_height: f64,
    pub dancer_arm_length: f64,
    pub dancer_arm_width: f64,
    pub dancer_arm_thickness: f64,
    pub pivot_bore: f64,
    pub bearing_od: f64,
    pub bearing_id: f64,
    pub bracket_base_width: f64,
    pub bracket_base_depth: f64,
    pub bracket_height: f64,
    pub pivot_post_height: f64,
}

#[derive(Deserialize)]
struct ConfigFile {
    default: Config,
}

/// Resolve the path to config.toml at the project root.
///
/// Tries in order:
/// 1. `VIAL_LAYBELL_CONFIG` environment variable
/// 2. `../../config.toml` relative to the vcad crate manifest directory (compile-time)
/// 3. `../../config.toml` relative to the current executable
fn resolve_config_path() -> PathBuf {
    if let Ok(p) = std::env::var("VIAL_LAYBELL_CONFIG") {
        return PathBuf::from(p);
    }

    // At compile time, CARGO_MANIFEST_DIR points to src/vcad/
    let manifest_relative = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../config.toml");
    if manifest_relative.exists() {
        return manifest_relative;
    }

    // Fallback: relative to executable location
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidate = dir.join("../../config.toml");
            if candidate.exists() {
                return candidate;
            }
        }
    }

    // Last resort — assume cwd
    PathBuf::from("config.toml")
}

/// Load and parse the project configuration.
pub fn load_config() -> Config {
    let path = resolve_config_path();
    let content = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("Failed to read config at {}: {}", path.display(), e));
    let file: ConfigFile = toml::from_str(&content)
        .unwrap_or_else(|e| panic!("Failed to parse config.toml: {}", e));
    file.default
}
