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

## Setup

See [docs/installation-guide.md](docs/installation-guide.md) for CAD environment setup.
