# Curve-Driven Label Routing

## What it demonstrates
The complete label/backing paper path through the applicator mechanism:
- Spool exit → dancer roller → guide roller → peel edge
- Peel separation: label continues to vial, backing wraps around peel radius and exits
- Feed visualization via curve trim/reveal driven by `CTRL.feed_mm`
- Dancer arm kinematics driven by `CTRL.dancer_deg`

## How it works
1. Waypoints from mechanical constants define the label path centerline
2. Roller wrap arcs are computed for dancer and guide rollers
3. At the peel edge, the path splits into backing exit and label exit curves
4. Geometry Nodes convert curves to ribbon meshes (Curve to Mesh + rectangle profile)
5. Trim/reveal GN modifier controls how much of each path is visible
6. Drivers on CTRL.feed_mm map feed distance to trim factor (0–1)

## How to run headless
```bash
blender -b -P tools/blender_labeler_anim/techniques/curve_driven/generate_and_render.py \
  -- --out tools/blender_labeler_anim/techniques/curve_driven/output \
  --frames 1 120 --fps 24 --samples 32
```

## Outputs
- `output/frame_0001.png` through `frame_0120.png` — rendered PNG frames
- `output/animation.mp4` — if `--encode-mp4` is passed and ffmpeg is available

## Key parameters
- `--frames 1 N` — number of frames (more = smoother, slower render)
- `--samples N` — Cycles samples (lower = faster, noisier)
- `--engine BLENDER_EEVEE_NEXT` — faster rendering alternative
- In script: modify `keyframe_ctrl()` to change animation timing
