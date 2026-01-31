"""Tests for config validation."""

import pytest

from config import load_config
from config_validator import ConfigValidationError, validate


class TestConfigValidation:
    """Test config validation catches invalid dimensions."""

    def test_valid_config_passes(self):
        """Default config passes validation."""
        cfg = load_config()
        validate(cfg)  # should not raise

    def test_valid_22mm_profile_passes(self):
        """22mm profile passes validation."""
        cfg = load_config(profile="22mm")
        validate(cfg)  # should not raise

    def test_missing_key_raises(self):
        """Missing required key raises ConfigValidationError."""
        cfg = load_config()
        del cfg["vial_diameter"]
        with pytest.raises(
            ConfigValidationError, match="Missing required key: vial_diameter"
        ):
            validate(cfg)

    def test_negative_dimension_raises(self):
        """Negative dimension raises ConfigValidationError."""
        cfg = load_config()
        cfg["vial_diameter"] = -1.0
        with pytest.raises(ConfigValidationError, match="vial_diameter.*below minimum"):
            validate(cfg)

    def test_zero_wall_thickness_raises(self):
        """Zero wall thickness raises ConfigValidationError."""
        cfg = load_config()
        cfg["wall_thickness"] = 0.0
        with pytest.raises(ConfigValidationError, match="wall_thickness.*below"):
            validate(cfg)

    def test_label_wider_than_frame_raises(self):
        """Label wider than frame raises ConfigValidationError."""
        cfg = load_config()
        cfg["label_width"] = cfg["frame_width"] + 10.0
        with pytest.raises(
            ConfigValidationError, match="label_width.*must be < frame_width"
        ):
            validate(cfg)

    def test_bearing_od_less_than_id_raises(self):
        """Bearing OD less than ID raises ConfigValidationError."""
        cfg = load_config()
        cfg["bearing_od"] = 5.0
        cfg["bearing_id"] = 10.0
        with pytest.raises(
            ConfigValidationError, match="bearing_od.*must be > bearing_id"
        ):
            validate(cfg)
