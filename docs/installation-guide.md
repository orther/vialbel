# Installation Guide

## Requirements

- Python 3.10+ (tested with 3.13)
- pip

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install build123d
```

## Verify

```bash
python src/test_cad_setup.py
```

Should output bounding box dimensions and export STL/3MF files to `models/test/`.

## Tooling

- **Build123d** (v0.10.0) - Parametric CAD library using OCCT kernel
- Exports STL and 3MF (native format for Bambu Studio)
- See [cad-tooling-research.md](cad-tooling-research.md) for selection rationale
