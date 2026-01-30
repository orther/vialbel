# Workflow Comparison

Three CAD tools available for the vial label applicator project, each with different strengths.

## Tool Summary

| | Build123d | vcad | Blender MCP |
|---|-----------|------|-------------|
| **Role** | Precision parts | Rapid prototyping | Visualization & rendering |
| **Language** | Python | Rust | Python (bpy) |
| **Geometry** | BREP (exact) | Mesh (approximate) | Mesh + modifiers |
| **Fillets** | Native | None | Bevel modifier |
| **Export** | STL, 3MF | STL, GLB | Any format |
| **AI integration** | Script generation | Agent-friendly API | MCP server |
| **Maturity** | Production | v0.1.0 | Production |

## Recommended Workflow

### For manufacturing (3D printing)
Use **Build123d**. BREP geometry ensures exact dimensions. Fillets and precise edge treatments are critical for functional parts that need to fit together.

```
Build123d script → STL/3MF → Bambu Studio → Print
```

### For rapid iteration
Use **vcad**. Fast compile times, simple API. Good for testing layout changes and basic geometry before committing to Build123d precision scripts.

```
vcad Rust script → STL → Quick preview
```

### For visualization and rendering
Use **Blender MCP**. Import STL files from either tool, apply materials, set up lighting, and produce product renders — all driven by Claude.

```
Build123d/vcad → STL → Blender MCP import → Materials → Render
```

### Full pipeline
```
1. Prototype with vcad (quick geometry)
2. Refine with Build123d (precision parts)
3. Visualize with Blender MCP (renders, assembly views)
```

## File Locations

| Tool | Source | Output |
|------|--------|--------|
| Build123d | `src/*.py` | `models/components/` |
| vcad | `src/vcad/src/*.rs` | `models/vcad/` |
| Blender | `src/blender/*.py` | Via Blender MCP |
