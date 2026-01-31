# Implementation Plan

## Stage 1: Cleanup & Consistency

**Goal**: Fix outstanding inconsistencies from initial implementation.

**Tasks**:

### 1.1 Remove test artifacts
- Delete `models/test/test_cylinder.stl` and `models/test/test_cylinder.3mf`
- Remove `models/test/` directory
- Remove `test/` line from README project structure (or keep if needed later)

### 1.2 Export missing dancer_arm.3mf
- `models/components/dancer_arm.stl` exists but has no `.3mf` counterpart
- All other 5 components have both formats
- Run `python src/tension_system.py` and verify `dancer_arm.3mf` is generated
- If export fails, debug the 3MF Mesher call in `tension_system.py`

### 1.3 Regenerate vcad STLs for new components
- `models/vcad/` only has 3 STLs (frame, peel plate, vial cradle)
- Run `cargo run --manifest-path src/vcad/Cargo.toml` to generate all 6
- Verify `spool_holder.stl`, `dancer_arm.stl`, `guide_roller_bracket.stl` appear

### 1.4 Remove stale test script
- `src/test_cad_setup.py` was a one-time verification script
- Delete it

**Success Criteria**: `models/components/` has 12 files (6 STL + 6 3MF), `models/vcad/` has 6 STLs, no test artifacts remain.

**Status**: Not Started

---

## Stage 2: Label Path Simulation

**Goal**: Model the physical label routing path through the machine.

**Spec**:
- Labels feed from spool → through dancer arm tension → over guide roller → through peel plate → onto vial
- The path defines critical geometry: roller positions, wrap angles, minimum bend radii
- Need to validate that label stock (0.15mm thick, semi-rigid) can navigate the path without jamming

**Tasks**:

### 2.1 Define label path geometry
- Create `src/label_path.py` with Build123d
- Define path as a series of waypoints: spool exit → dancer roller contact → guide roller contact → peel plate entry → peel edge → vial surface
- Each waypoint: (x, y, z) position + tangent direction + wrap angle
- Parameters: label width (40mm), label thickness (0.15mm), minimum bend radius (5mm)

### 2.2 Generate path visualization
- Create a 3D spline/sweep along the waypoints
- Export as STL for Blender overlay on assembly
- Color-code sections: feed (blue), tension (yellow), peel (red), application (green)

### 2.3 Validate path constraints
- Check all bend radii ≥ minimum (5mm for thermal label stock)
- Check label doesn't intersect any component geometry
- Check total path length matches expected label strip dimensions
- Print validation report to stdout

**Success Criteria**: `python src/label_path.py` generates path STL and prints validation report with all constraints passing.

**Status**: Not Started

---

## Stage 3: Parametric Configuration

**Goal**: Single config file drives all component dimensions for different vial sizes.

**Spec**:
- Currently each script has hardcoded dimensions (vial_diameter=16, label_width=40, etc.)
- Need a shared config so changing vial size cascades to all components
- Support at minimum: 16mm vial (current), 22mm vial (common lab size)

**Tasks**:

### 3.1 Create config schema
- Create `src/config.py` with a dataclass or dict
- Parameters: vial_diameter, vial_height, label_width, label_height, label_offset_from_bottom, material_thickness
- Derived values: cradle_v_angle, peel_plate_channel_width, frame_width
- Load from `config.toml` in project root, with defaults matching current 16mm design

### 3.2 Create config.toml
- Create `config.toml` with current hardcoded values as defaults
- Add a `[profiles.22mm]` section for 22mm vial variant
- CLI usage: `python src/peel_plate.py` (default) or `python src/peel_plate.py --profile 22mm`

### 3.3 Refactor component scripts
- Update `src/peel_plate.py` to read from config instead of module-level constants
- Update `src/vial_cradle.py` — vial_diameter, cradle_length, base_width
- Update `src/tension_system.py` — spool dimensions stay fixed, but label_width affects dancer
- Update `src/frame.py` — frame dimensions derived from component sizes
- Each script: `from config import load_config; cfg = load_config()`

### 3.4 Validate both profiles
- Run all scripts with default profile → verify output matches current models
- Run all scripts with 22mm profile → verify all components scale correctly
- Diff STL bounding boxes between profiles to confirm expected size changes

**Success Criteria**: `python src/frame.py --profile 22mm` generates a valid frame sized for 22mm vials. Default profile output matches existing models byte-for-byte.

**Status**: Not Started

---

## Stage 4: Assembly Constraints

**Goal**: Derive component positions from frame geometry instead of hardcoded offsets.

**Spec**:
- `src/blender/import_assembly.py` has manually specified positions for each component
- `src/frame.py` already calculates where components attach (slot positions, hole locations)
- These should be a single source of truth

**Tasks**:

### 4.1 Extract positions from frame script
- Add a `get_component_positions()` function to `src/frame.py`
- Returns dict: `{"peel_plate": (x, y, z, rx, ry, rz), "vial_cradle": ..., ...}`
- Positions derived from frame geometry calculations already in the script

### 4.2 Create shared assembly manifest
- Create `models/assembly_manifest.json` generated by `src/frame.py`
- Schema: `{"components": [{"name": "...", "stl": "...", "position": [...], "rotation": [...], "color": [...]}]}`
- Generated as side effect of running `python src/frame.py`

### 4.3 Update Blender import script
- Refactor `src/blender/import_assembly.py` to read from `assembly_manifest.json`
- Remove hardcoded COMPONENTS list
- Keep color assignments (aesthetic choice, not geometric)

### 4.4 Update vcad main.rs (optional)
- If vcad components need positioning, read the same manifest
- Low priority since vcad exports individual parts, not assemblies

**Success Criteria**: Changing a component position in `src/frame.py` automatically updates the Blender import. No position values duplicated between files.

**Status**: Not Started

---

## Stage 5: Print Validation

**Goal**: Automated checks that models are 3D-printable on target printer (Bambu P1S, ASA).

**Spec**:
- Common print failures: walls too thin (<0.8mm for 0.4mm nozzle), overhangs >45°, non-manifold geometry
- Should catch issues before sending to slicer

**Tasks**:

### 5.1 Wall thickness check
- For each component STL, find minimum wall thickness
- Flag any wall < 0.8mm (single wall) or < 1.2mm (structural)
- Use mesh analysis: ray casting or cross-section sampling
- Build123d can compute this via section planes

### 5.2 Overhang analysis
- For each triangle face, compute angle from build plate normal
- Flag faces with overhang angle > 45° that aren't supported by geometry below
- Report: percentage of unsupported overhangs, worst-case angle
- Note: P1S has decent overhang capability at 50°, but 45° is safe target

### 5.3 Manifold check
- Verify all exported STLs are watertight (no holes, no self-intersections)
- Use `trimesh` library: `mesh.is_watertight`, `mesh.is_volume`
- Flag non-manifold edges and vertices

### 5.4 Create validation script
- Create `src/validate_prints.py`
- Reads all STLs from `models/components/`
- Runs checks 5.1-5.3 on each
- Prints pass/fail report with details on failures
- Exit code 0 if all pass, 1 if any fail

**Success Criteria**: `python src/validate_prints.py` runs all checks and reports results. All current components pass.

**Status**: Not Started

---

## Stage 6: CI Pipeline

**Goal**: Automated verification on push.

**Spec**:
- GitHub Actions workflow
- Fast feedback: should complete in under 5 minutes

**Tasks**:

### 6.1 Rust check job
- `cargo check --manifest-path src/vcad/Cargo.toml`
- `cargo clippy --manifest-path src/vcad/Cargo.toml -- -D warnings`
- Runs on ubuntu-latest

### 6.2 Python lint job
- Install ruff or flake8
- Lint `src/*.py` and `src/blender/*.py`
- Check formatting consistency

### 6.3 Build123d model generation job (optional)
- Install Build123d in CI (requires OCCT — may be heavy)
- Run all component scripts
- Verify STL outputs are non-empty
- This may be too slow/complex for CI — evaluate feasibility first

### 6.4 Create workflow file
- Create `.github/workflows/ci.yml`
- Jobs: rust-check, python-lint, (optional) model-generation
- Trigger on push to main and PRs

**Success Criteria**: PRs get automatic checks. Rust compilation and Python lint run in under 2 minutes.

**Status**: Not Started

---

## Stage 7: Blender Render Automation

**Goal**: Render product shots from CLI without requiring MCP connection.

**Spec**:
- Currently renders require: Blender open → MCP addon connected → Claude sends commands
- Should be possible to run headless: `blender --background --python src/blender/render_all.py`

**Tasks**:

### 7.1 Create headless render script
- Create `src/blender/render_all.py`
- Combines import_assembly.py + render_setup.py into single headless script
- Configurable: output directory, resolution, sample count, camera angles
- Uses `sys.argv` after `--` for Blender CLI arg passing

### 7.2 Define camera presets
- Hero shot (3/4 angle from front-right)
- Top-down (orthographic or near-orthographic)
- Front detail (low angle, component focus)
- Exploded view (components separated along Z axis with offset)

### 7.3 Add render to Makefile or script
- Create `scripts/render.sh` or add to a Makefile
- Command: `make renders` or `./scripts/render.sh`
- Checks Blender is installed, runs headless, outputs to `models/renders/`

### 7.4 HDRI setup without PolyHaven
- Current setup downloads HDRI via PolyHaven MCP integration
- Headless script needs a bundled or downloaded HDRI
- Option: download a CC0 HDRI to `assets/` on first run, or use Blender's built-in sky texture

**Success Criteria**: `blender --background --python src/blender/render_all.py -- --output models/renders/` produces all 4 camera angle renders without MCP.

**Status**: Not Started
