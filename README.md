# Vial Label Applicator

3D-printable semi-automated thermal label applicator for small vials. Applies wrap-around thermal labels (40mm x 20mm, NiimBot M2) to 3mL cylindrical vials (16mm diameter x 38.5mm tall).

## Key Specs

| Parameter | Value |
|-----------|-------|
| Vial diameter | 16mm (22mm profile available) |
| Vial height | 38.5mm |
| Label size | 40mm x 20mm |
| Label position | 3mm from vial bottom |
| Material | ASA (Bambu Lab P1S) |
| Throughput | 2-3 seconds per vial |

## Project Structure

```
config.toml             - Parametric dimensions (profiles: default, 22mm)
src/                    - Parametric CAD scripts (Build123d, Python)
  config.py             - Config loader with profile support
  frame.py              - Main frame + assembly manifest generation
  peel_plate.py         - Label dispensing peel plate
  vial_cradle.py        - V-block vial holder
  tension_system.py     - Spool holder, dancer arm, guide roller bracket
  label_path.py         - Label routing simulation and validation
  validate_prints.py    - 3D print validation (manifold, overhang, wall thickness)
src/vcad/               - Parametric CAD scripts (vcad, Rust)
src/blender/            - Blender visualization and rendering
  import_assembly.py    - Import assembly via Blender MCP
  render_all.py         - Headless render script (3 camera presets)
models/
  components/           - Build123d-generated STL/3MF files
  vcad/                 - vcad-generated STL files
  assembly_manifest.json - Component positions (single source of truth)
  renders/              - Rendered assembly images
tests/                  - Integration tests (pytest)
.github/workflows/      - CI pipeline (Rust + Python + tests)
```

## Components

1. **Main Frame** — Base plate with mounting wall, pivot post, and mounting holes
2. **Peel Plate** — Label dispensing with 2mm radius peel edge
3. **Vial Cradle** — V-block holder with height positioning
4. **Tension System** — Spool holder, spring-loaded dancer arm, guide roller bracket
5. **Label Path** — Simulated routing: spool → dancer → guide → peel plate → vial

## Parametric Configuration

All dimensions are defined in `config.toml`. Switch vial sizes with profiles:

```bash
# Default 16mm vial
python src/peel_plate.py

# 22mm vial profile
python src/peel_plate.py --profile 22mm
```

Both Python (Build123d) and Rust (vcad) pipelines read from the same `config.toml`.

## Regenerating Models

### Build123d (precision parts)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install build123d

python src/frame.py              # Frame + assembly manifest
python src/peel_plate.py         # Peel plate
python src/vial_cradle.py        # Vial cradle
python src/tension_system.py     # Spool holder, dancer arm, guide roller bracket
python src/label_path.py         # Label path simulation + visualization STL
```

### vcad (rapid prototypes, Rust)

```bash
cargo run --manifest-path src/vcad/Cargo.toml
```

### Print Validation

```bash
pip install trimesh numpy rtree
python src/validate_prints.py
```

### Headless Rendering

```bash
blender --background --python src/blender/render_all.py -- \
    --output models/renders/ --resolution 1920x1080 --samples 128
```

Or use the convenience script:

```bash
./scripts/render.sh
```

## Testing

```bash
pip install pytest ruff
python -m pytest tests/ -v
```

Tests validate config loading, profile overrides, manifest structure, STL file existence, and code quality (ruff lint/format) — no build123d required.

## CI

GitHub Actions runs three jobs on push/PR to main:
- **Rust Check** — `cargo check` + `cargo clippy`
- **Python Lint** — `ruff check` + `ruff format --check`
- **Integration Tests** — pytest suite

## Documentation

- [Installation Guide](docs/installation-guide.md) — CAD environment setup
- [Print Settings](docs/print-settings.md) — Bambu Studio ASA profiles
- [Hardware BOM](docs/hardware-bom.md) — Non-printed parts list
- [Assembly Guide](docs/assembly-guide.md) — Step-by-step assembly
- [Calibration Guide](docs/calibration-guide.md) — First-time setup
- [Blender MCP Setup](docs/blender-mcp-setup.md) — Blender integration via MCP
