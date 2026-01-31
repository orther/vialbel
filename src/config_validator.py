"""Config validation for vial label applicator dimensions."""

REQUIRED_KEYS = [
    "vial_diameter",
    "vial_height",
    "label_width",
    "label_height",
    "label_offset_from_bottom",
    "label_thickness",
    "min_bend_radius",
    "wall_thickness",
    "base_thickness",
    "mount_hole_diameter",
    "fillet_radius",
    "frame_length",
    "frame_width",
    "frame_wall_height",
    "frame_wall_thickness",
    "peel_channel_width_clearance",
    "peel_body_depth",
    "peel_body_height_rear",
    "peel_mount_hole_spacing",
    "cradle_base_height",
    "cradle_v_block_height",
    "cradle_mount_slot_spacing_x",
    "cradle_mount_slot_spacing_y",
    "spool_spindle_od",
    "spool_flange_diameter",
    "spool_flange_thickness",
    "spool_height",
    "dancer_arm_length",
    "dancer_arm_width",
    "dancer_arm_thickness",
    "pivot_bore",
    "bearing_od",
    "bearing_id",
    "bracket_base_width",
    "bracket_base_depth",
    "bracket_height",
    "pivot_post_height",
]

# Minimum physical dimension for 3D printing (mm)
MIN_DIMENSION = 0.1
MIN_WALL = 0.8
MAX_DIMENSION = 500.0


class ConfigValidationError(ValueError):
    """Raised when config values are invalid."""

    pass


def validate(cfg: dict) -> None:
    """Validate config values. Raises ConfigValidationError with all issues."""
    errors = []

    # 1. Required keys
    for key in REQUIRED_KEYS:
        if key not in cfg:
            errors.append(f"Missing required key: {key}")

    # 2. Type validation (all must be numeric)
    for key in REQUIRED_KEYS:
        if key in cfg and not isinstance(cfg[key], (int, float)):
            errors.append(f"{key}: expected number, got {type(cfg[key]).__name__}")

    # Stop here if missing keys or wrong types
    if errors:
        raise ConfigValidationError("\n".join(errors))

    # 3. Range validation
    positive_dims = [
        "vial_diameter",
        "vial_height",
        "label_width",
        "label_height",
        "label_thickness",
        "wall_thickness",
        "base_thickness",
        "frame_length",
        "frame_width",
        "frame_wall_height",
        "frame_wall_thickness",
        "peel_body_depth",
        "peel_body_height_rear",
        "spool_spindle_od",
        "spool_flange_diameter",
        "spool_flange_thickness",
        "spool_height",
        "dancer_arm_length",
        "dancer_arm_width",
        "dancer_arm_thickness",
        "pivot_bore",
        "bearing_od",
        "bearing_id",
        "bracket_base_width",
        "bracket_base_depth",
        "bracket_height",
        "pivot_post_height",
        "mount_hole_diameter",
    ]
    for key in positive_dims:
        val = cfg[key]
        if val < MIN_DIMENSION:
            errors.append(f"{key}: {val}mm is below minimum ({MIN_DIMENSION}mm)")
        if val > MAX_DIMENSION:
            errors.append(f"{key}: {val}mm exceeds maximum ({MAX_DIMENSION}mm)")

    if cfg["wall_thickness"] < MIN_WALL:
        errors.append(
            f"wall_thickness: {cfg['wall_thickness']}mm below printable minimum ({MIN_WALL}mm)"
        )

    # 4. Cross-field constraints
    if cfg["label_width"] >= cfg["frame_width"]:
        errors.append(
            f"label_width ({cfg['label_width']}mm) must be < frame_width ({cfg['frame_width']}mm)"
        )
    if cfg["label_height"] >= cfg["vial_height"]:
        errors.append(
            f"label_height ({cfg['label_height']}mm) must be < vial_height ({cfg['vial_height']}mm)"
        )
    if cfg["label_offset_from_bottom"] + cfg["label_height"] > cfg["vial_height"]:
        errors.append("label_offset + label_height exceeds vial_height")
    if cfg["spool_flange_diameter"] <= cfg["spool_spindle_od"]:
        errors.append(
            f"spool_flange_diameter ({cfg['spool_flange_diameter']}mm) must be > spool_spindle_od ({cfg['spool_spindle_od']}mm)"
        )
    if cfg["bearing_od"] <= cfg["bearing_id"]:
        errors.append(
            f"bearing_od ({cfg['bearing_od']}mm) must be > bearing_id ({cfg['bearing_id']}mm)"
        )

    if errors:
        raise ConfigValidationError("\n".join(errors))
