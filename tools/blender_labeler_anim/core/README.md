# Core Modules

Shared infrastructure for the Blender label applicator animation system.

## Modules

- **constants.py** — Mechanical coordinates, radii, and label parameters
- **units.py** — Scene unit configuration (millimeters)
- **materials.py** — Material factory functions (label, backing, glass, metal)
- **cli.py** — CLI argument parsing for `blender -b -P script.py -- [args]`
- **render.py** — Render settings, output config, frame/animation rendering, MP4 encoding
- **generate_scene.py** — Base scene creation (camera, lights, ground, vial, rollers, CTRL empty)
- **geom_nodes_lib.py** — Geometry Nodes programmatic builders

## CTRL Empty

All animation is driven from custom properties on the `CTRL` empty:
- `feed_mm` — Label feed distance (0–200mm)
- `vial_rot_deg` — Vial rotation (0–360°)
- `dancer_deg` — Dancer arm angle (±30°)

## Usage

```python
import sys
sys.path.insert(0, '/path/to/tools/blender_labeler_anim')
from core.generate_scene import build_base_scene
from core.render import setup_render, render_animation
from core.cli import parse_args

args = parse_args()
objects = build_base_scene()
setup_render(engine=args.engine, samples=args.samples, resolution=tuple(args.resolution), fps=args.fps, frame_range=tuple(args.frames))
```
