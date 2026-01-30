# Vial Label Applicator

3D-printable semi-automated thermal label applicator for small vials. Applies wrap-around thermal labels (40mm x 20mm, NiimBot M2) to 3mL cylindrical vials (16mm diameter x 38.5mm tall).

## Key Specs

| Parameter | Value |
|-----------|-------|
| Vial diameter | 16mm |
| Vial height | 38.5mm |
| Label size | 40mm x 20mm |
| Label position | 3mm from vial bottom |
| Material | ASA (Bambu Lab P1S) |
| Throughput | 2-3 seconds per vial |

## Project Structure

```
src/            - Parametric CAD scripts
models/         - Generated 3D files (STL, 3MF)
  test/         - Test/verification models
  components/   - Individual part models
  assembly/     - Full assembly models
docs/           - Documentation
reference/      - Research notes
```

## Components

1. **Peel Plate** - Label dispensing with 2mm radius peel edge
2. **Vial Cradle** - V-block holder with height positioning
3. **Tension System** - Spring-loaded backing paper tension
4. **Main Frame** - Integrates all components

## Generated Models

| Component | Bounding Box (mm) | Script |
|-----------|-------------------|--------|
| Peel Plate | 46 x 25 x 15 | `src/peel_plate.py` |
| Vial Cradle | 53 x 36 x 23 | `src/vial_cradle.py` |
| Spool Holder | 40 x 40 x 33 | `src/tension_system.py` |
| Dancer Arm | 82 x 27 x 5 | `src/tension_system.py` |
| Guide Roller Bracket | 25 x 20 x 28 | `src/tension_system.py` |
| Main Frame | 200 x 120 x 45 | `src/frame.py` |

STL and 3MF files in `models/components/`. Assembly visualization in `models/assembly/`.

## Documentation

- [Installation Guide](docs/installation-guide.md) - CAD environment setup
- [Print Settings](docs/print-settings.md) - Bambu Studio ASA profiles
- [Hardware BOM](docs/hardware-bom.md) - Non-printed parts list
- [Assembly Guide](docs/assembly-guide.md) - Step-by-step assembly
- [Calibration Guide](docs/calibration-guide.md) - First-time setup
- [CAD Tooling Research](docs/cad-tooling-research.md) - Tool selection rationale

## Regenerating Models

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install build123d
python src/peel_plate.py
python src/vial_cradle.py
python src/tension_system.py
python src/frame.py
```
