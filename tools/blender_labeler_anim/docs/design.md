# Design: Blender Label Applicator Animation System

## Overview

A headless, scripted Blender animation system for visualizing a mechanical vial label applicator. The system generates all geometry, materials, and animation from Python scripts with no manual Blender interaction required.

## Architecture

### Core Layer (`core/`)
Shared infrastructure used by all techniques:
- **Scene generation**: Camera, lighting, ground plane, mechanical components (vial, rollers, peel plate)
- **CTRL Empty**: Single animation controller with `feed_mm`, `vial_rot_deg`, `dancer_deg` custom properties
- **Materials**: Principled BSDF-based materials for label, backing, glass, metal
- **Render pipeline**: Cycles/EEVEE-Next configuration, PNG output, optional MP4 encoding
- **Geometry Nodes library**: Programmatic node group construction (curve-to-ribbon, trim/reveal)

### Technique Layer (`techniques/`)
Three independent implementations, each self-contained:

1. **Curve-Driven** — Label/backing paths as Blender curves with ribbon mesh via GN
2. **Wrap Handoff** — Two-geometry system: flat strip near peel edge + cylindrical patch on vial
3. **Geometry Nodes Polar Wrap** — Pure GN coordinate deformation from flat to cylindrical

### Control Flow
```
CTRL.feed_mm ──► Curve trim/reveal ──► Label feed visualization
CTRL.vial_rot_deg ──► Vial rotation ──► Wrap amount (handoff or polar)
CTRL.dancer_deg ──► Dancer arm rotation ──► Tension arm kinematics
```

All motion is driven via Blender drivers referencing CTRL properties. No simulation or physics; fully deterministic.

## Determinism Guarantee

- No cloth/soft-body simulation
- No random seeds in geometry generation
- All positions computed from parametric equations
- Curves defined by explicit control points
- Geometry Nodes use deterministic operations only
- Repeated runs with same parameters produce identical output

## Coordinate System

- X: left(-) to right(+)
- Y: back(-) to front(+)
- Z: bottom(0) to top(+)
- Units: millimeters (scene scale = 0.001)

## Rendering

- Default engine: Cycles (GPU via Metal on macOS)
- Fallback: EEVEE-Next for faster previews
- Output: PNG frames with optional ffmpeg MP4 encoding
- Headless: `blender -b -P script.py -- [args]`
