# Wrap Technique A: Two-Geometry Handoff

## What it demonstrates
A deterministic "engineering visualization" of label wrapping using two separate
geometries: a flat label strip near the peel edge and a pre-shaped cylindrical
patch on the vial surface. As wrapping progresses, the wrapped patch is revealed
while the flat strip is hidden — creating the illusion of continuous wrapping.

## How it works
1. **Flat label strip**: A subdivided planar mesh positioned between the peel edge
   and vial contact point, with a slight arc for visual appeal.
2. **Wrapped label patch**: A cylindrical mesh pre-shaped to conform to the vial
   surface (offset 0.3mm above to avoid z-fighting), covering up to 270°.
3. **Handoff mechanism**: Geometry Nodes modifiers on each mesh use vertex index
   ratio as a position proxy. A Factor input (driven by `CTRL.vial_rot_deg`)
   controls which portions are visible:
   - Wrapped patch: vertices with index ratio < factor are kept (progressive reveal)
   - Flat strip: vertices with index ratio > factor are kept (progressive hide)
4. **Vial rotation**: The vial's Y rotation is driven by `CTRL.vial_rot_deg`,
   so the wrapped patch stays aligned as the vial turns.

## How to run headless
```bash
blender -b -P tools/blender_labeler_anim/techniques/wrap_handoff/generate_and_render.py \
  -- --out tools/blender_labeler_anim/techniques/wrap_handoff/output \
  --frames 1 120 --fps 24 --samples 32
```

## Outputs
- `output/frame_0001.png` through `frame_0120.png`
- `output/animation.mp4` (with `--encode-mp4`)

## Key parameters
- Wrap coverage: 270° (set in `constants.LABEL_WRAP_ANGLE`)
- Surface offset: 0.3mm above vial radius (prevents z-fighting)
- Mesh resolution: 80 segments around circumference, 4 along axis
