# PR Notes

## chore/blender-labeler-core

### Summary
Core scaffolding for the Blender label applicator animation system.

### Changes
- Created `tools/blender_labeler_anim/` directory structure
- Implemented shared core modules:
  - `constants.py` — Mechanical coordinates and parameters
  - `units.py` — Scene unit configuration (mm)
  - `materials.py` — Material factories
  - `cli.py` — CLI argument parsing
  - `render.py` — Render configuration and execution
  - `generate_scene.py` — Base scene builder
  - `geom_nodes_lib.py` — Geometry Nodes helpers
- Added documentation: design.md, troubleshooting.md

### How to Run
```bash
# Verify core modules load in Blender
blender -b -P tools/blender_labeler_anim/core/generate_scene.py
```
