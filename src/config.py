"""
Parametric configuration loader for the vial label applicator.

Reads config.toml from the project root and merges profile overrides.
Usage:
    from config import load_config
    cfg = load_config()  # uses default profile
    cfg = load_config("22mm")  # uses 22mm vial profile
"""

import argparse
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python < 3.11 fallback

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


def load_config(profile: str | None = None) -> dict:
    """Load configuration, optionally applying a named profile.

    Args:
        profile: Name of a profile from [profiles.<name>] in config.toml.
                 If None, checks sys.argv for --profile flag, then uses defaults.
    Returns:
        Flat dict of all configuration values.
    """
    if profile is None:
        profile = _parse_profile_from_argv()

    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)

    cfg = dict(raw["default"])

    if profile:
        profiles = raw.get("profiles", {})
        if profile not in profiles:
            available = ", ".join(profiles.keys()) or "(none)"
            raise ValueError(f"Unknown profile '{profile}'. Available: {available}")
        cfg.update(profiles[profile])

    # Derived values
    cfg.setdefault(
        "peel_channel_width",
        cfg["label_width"] + cfg.get("peel_channel_width_clearance", 1.0),
    )
    cfg.setdefault("cradle_base_width", cfg["vial_diameter"] + 20.0)
    cfg.setdefault("cradle_length", cfg["vial_diameter"] + 19.0)

    return cfg


def _parse_profile_from_argv() -> str | None:
    """Extract --profile from sys.argv without interfering with other parsers."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile", default=None)
    args, _ = parser.parse_known_args()
    return args.profile
