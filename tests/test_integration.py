"""
Integration tests for vial-laybell Python CAD project.

These tests verify the project structure and Python scripts work correctly
WITHOUT requiring build123d or OCCT (which are difficult to install in CI).

Tests verify:
- Configuration loading and validation
- Assembly manifest structure and validity
- Referenced STL files exist
- Code quality with ruff linting and formatting
"""

import json
import subprocess
from pathlib import Path

import pytest

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.toml"
MANIFEST_PATH = PROJECT_ROOT / "models" / "assembly_manifest.json"
COMPONENTS_DIR = PROJECT_ROOT / "models" / "components"
SRC_DIR = PROJECT_ROOT / "src"


@pytest.fixture
def config():
    """Load default configuration."""
    # Import here to avoid build123d dependency issues
    from config import load_config

    return load_config()


@pytest.fixture
def config_22mm():
    """Load 22mm profile configuration."""
    from config import load_config

    return load_config(profile="22mm")


@pytest.fixture
def manifest():
    """Load assembly manifest JSON."""
    with open(MANIFEST_PATH) as f:
        return json.load(f)


class TestConfigLoading:
    """Test configuration loading from config.toml."""

    def test_config_loads(self, config):
        """Verify load_config() loads config.toml and returns expected keys."""
        # Essential vial parameters
        assert "vial_diameter" in config
        assert "vial_height" in config

        # Label parameters
        assert "label_width" in config
        assert "label_height" in config
        assert "label_offset_from_bottom" in config

        # Frame dimensions
        assert "frame_length" in config
        assert "frame_width" in config
        assert "frame_wall_height" in config

        # Material settings
        assert "wall_thickness" in config
        assert "base_thickness" in config

        # Verify default values match config.toml [default] section
        assert config["vial_diameter"] == 16.0
        assert config["vial_height"] == 38.5
        assert config["label_width"] == 40.0
        assert config["frame_length"] == 200.0

    def test_config_profile_override(self, config, config_22mm):
        """Verify load_config(profile='22mm') returns different values."""
        # Values that should be overridden in 22mm profile
        assert config_22mm["vial_diameter"] == 22.0
        assert config_22mm["vial_height"] == 50.0
        assert config_22mm["label_width"] == 55.0
        assert config_22mm["label_height"] == 25.0
        assert config_22mm["frame_length"] == 240.0
        assert config_22mm["frame_width"] == 140.0

        # Verify they differ from default
        assert config_22mm["vial_diameter"] != config["vial_diameter"]
        assert config_22mm["label_width"] != config["label_width"]
        assert config_22mm["frame_length"] != config["frame_length"]

    def test_config_derived_values(self, config):
        """Verify computed values like peel_channel_width are derived correctly."""
        # peel_channel_width = label_width + peel_channel_width_clearance
        expected_peel_width = config["label_width"] + config.get(
            "peel_channel_width_clearance", 1.0
        )
        assert config["peel_channel_width"] == expected_peel_width
        assert config["peel_channel_width"] == 41.0  # 40.0 + 1.0 for default

        # cradle_base_width = vial_diameter + 20.0
        expected_cradle_width = config["vial_diameter"] + 20.0
        assert config["cradle_base_width"] == expected_cradle_width
        assert config["cradle_base_width"] == 36.0  # 16.0 + 20.0

        # cradle_length = vial_diameter + 19.0
        expected_cradle_length = config["vial_diameter"] + 19.0
        assert config["cradle_length"] == expected_cradle_length
        assert config["cradle_length"] == 35.0  # 16.0 + 19.0

    def test_config_invalid_profile_raises_error(self):
        """Verify loading an invalid profile raises ValueError."""
        from config import load_config

        with pytest.raises(ValueError, match="Unknown profile 'nonexistent'"):
            load_config(profile="nonexistent")


class TestAssemblyManifest:
    """Test assembly manifest JSON structure and validity."""

    def test_manifest_valid_json(self, manifest):
        """Verify assembly_manifest.json is valid JSON with expected structure."""
        assert isinstance(manifest, list)
        assert len(manifest) > 0

        # Each entry should have required fields
        required_fields = ["name", "file", "position", "rotation", "color"]
        for component in manifest:
            assert isinstance(component, dict)
            for field in required_fields:
                assert field in component, (
                    f"Component {component.get('name')} missing {field}"
                )

            # Validate field types
            assert isinstance(component["name"], str)
            assert isinstance(component["file"], str)
            assert isinstance(component["position"], list)
            assert isinstance(component["rotation"], list)
            assert isinstance(component["color"], list)

            # Position and rotation should be 3D vectors
            assert len(component["position"]) == 3
            assert len(component["rotation"]) == 3
            assert all(isinstance(x, (int, float)) for x in component["position"])
            assert all(isinstance(x, (int, float)) for x in component["rotation"])

            # Color should be RGBA
            assert len(component["color"]) == 4
            assert all(isinstance(x, (int, float)) for x in component["color"])

    def test_manifest_stl_files_exist(self, manifest):
        """Verify each STL file referenced in the manifest exists in models/components/."""
        missing_files = []
        for component in manifest:
            stl_path = COMPONENTS_DIR / component["file"]
            if not stl_path.exists():
                missing_files.append(component["file"])

        assert not missing_files, f"Missing STL files: {missing_files}"

    def test_manifest_positions_reasonable(self, manifest):
        """Verify component positions are within expected bounds (±200mm)."""
        # For a desktop label applicator, components shouldn't be more than 200mm
        # from origin in any direction
        max_reasonable_distance = 200.0

        out_of_bounds = []
        for component in manifest:
            position = component["position"]
            for axis, coord in zip(["X", "Y", "Z"], position):
                if abs(coord) > max_reasonable_distance:
                    out_of_bounds.append(
                        f"{component['name']}: {axis}={coord}mm exceeds ±{max_reasonable_distance}mm"
                    )

        assert not out_of_bounds, "Components out of bounds:\n" + "\n".join(
            out_of_bounds
        )

    def test_manifest_colors_valid(self, manifest):
        """Verify RGBA color values are between 0.0 and 1.0."""
        invalid_colors = []
        for component in manifest:
            color = component["color"]
            for i, value in enumerate(color):
                if not 0.0 <= value <= 1.0:
                    channel = ["R", "G", "B", "A"][i]
                    invalid_colors.append(
                        f"{component['name']}: {channel}={value} not in [0.0, 1.0]"
                    )

        assert not invalid_colors, "Invalid color values:\n" + "\n".join(
            invalid_colors
        )

    def test_manifest_component_names(self, manifest):
        """Verify expected components are present in manifest."""
        component_names = {comp["name"] for comp in manifest}

        # Expected components based on the project structure
        expected_components = {
            "Frame",
            "PeelPlate",
            "VialCradle",
            "SpoolHolder",
            "DancerArm",
            "GuideRollerBracket",
        }

        missing = expected_components - component_names
        assert not missing, f"Missing expected components: {missing}"


class TestCodeQuality:
    """Test code quality with ruff linting and formatting."""

    def test_ruff_lint(self):
        """Run 'uvx ruff check src/*.py' and verify it passes."""
        # Get all Python files in src/
        py_files = list(SRC_DIR.glob("*.py"))
        assert len(py_files) > 0, "No Python files found in src/"

        result = subprocess.run(
            ["uvx", "ruff", "check"] + [str(f) for f in py_files],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Ruff linting failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    def test_ruff_format(self):
        """Run 'uvx ruff format --check src/*.py' and verify it passes."""
        # Get all Python files in src/
        py_files = list(SRC_DIR.glob("*.py"))
        assert len(py_files) > 0, "No Python files found in src/"

        result = subprocess.run(
            ["uvx", "ruff", "format", "--check"] + [str(f) for f in py_files],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Ruff formatting check failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


class TestProjectStructure:
    """Test project file structure and dependencies."""

    def test_config_toml_exists(self):
        """Verify config.toml exists at project root."""
        assert CONFIG_PATH.exists(), "config.toml not found at project root"

    def test_manifest_json_exists(self):
        """Verify assembly_manifest.json exists in models/."""
        assert MANIFEST_PATH.exists(), "assembly_manifest.json not found in models/"

    def test_components_directory_exists(self):
        """Verify models/components/ directory exists."""
        assert COMPONENTS_DIR.exists(), "models/components/ directory not found"
        assert COMPONENTS_DIR.is_dir(), "models/components/ is not a directory"

    def test_src_directory_has_python_files(self):
        """Verify src/ contains Python files."""
        py_files = list(SRC_DIR.glob("*.py"))
        assert len(py_files) > 0, "No Python files found in src/"

        # Verify key files exist
        expected_files = ["config.py"]
        for filename in expected_files:
            assert (SRC_DIR / filename).exists(), f"Expected {filename} in src/"
