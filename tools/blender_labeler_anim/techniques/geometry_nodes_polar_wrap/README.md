# Wrap Technique B: Pure Geometry Nodes Polar Wrap

## What it demonstrates
A coordinate-space deformation that morphs a flat label strip into a cylindrical
wrap around the vial — entirely within Geometry Nodes, with no separate geometries.

## How it works
1. A flat, subdivided label mesh is created at the peel edge position
2. A Geometry Nodes modifier performs polar coordinate mapping:
   - Each vertex's X position (along the wrap direction) maps to an angle:
     `angle = (x / wrap_length) * wrap_max_angle * wrap_factor`
   - New positions computed relative to vial center:
     `x' = vial_cx + (r + eps) * cos(start_angle - angle)`
     `z' = vial_cz + (r + eps) * sin(start_angle - angle)`
     `y' = vial_cy + original_y`
3. A blend zone provides smooth transition from flat-at-peel to cylindrical:
   - Vertices near the current wrap front smoothly interpolate between flat and wrapped
   - Vertices beyond the wrap extent remain at the peel edge (or are hidden)
4. The `Wrap Factor` input (0–1) is driven by `CTRL.vial_rot_deg / 270`

## How to run headless
```bash
blender -b -P tools/blender_labeler_anim/techniques/geometry_nodes_polar_wrap/generate_and_render.py \
  -- --out tools/blender_labeler_anim/techniques/geometry_nodes_polar_wrap/output \
  --frames 1 120 --fps 24 --samples 32
```

## Outputs
- `output/frame_0001.png` through `frame_0120.png`
- `output/animation.mp4` (with `--encode-mp4`)

## Key parameters
- `Wrap Factor`: 0 = fully flat, 1 = fully wrapped (270°)
- `Blend Zone`: transition width in mm (default 5mm) — controls smoothness
- Surface offset: 0.3mm above vial radius
- Mesh resolution: 100 segments along wrap, 6 across width
