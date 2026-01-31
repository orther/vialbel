# vcad Setup

Rust-based parametric CSG modeling for rapid prototyping of vial applicator components.

## Prerequisites

- Rust toolchain (install via `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- CMake and Ninja (`brew install cmake ninja`)

## Building

```bash
cargo build --manifest-path src/vcad/Cargo.toml
```

## Generating Models

```bash
cargo run --manifest-path src/vcad/Cargo.toml
```

Outputs STL files to `models/vcad/`:
- `peel_plate.stl` — Simplified peel plate (box body, no wedge profile or fillets)
- `vial_cradle.stl` — V-block cradle with angled cut
- `main_frame.stl` — Base plate with wall, pivot post, mounting holes

## vcad vs Build123d

| Feature | vcad | Build123d |
|---------|------|-----------|
| Language | Rust | Python |
| Kernel | Manifold (mesh) | OCCT (BREP) |
| Fillets | No native support | Full BREP fillets |
| Precision | Mesh approximation | Mathematically exact |
| Export | STL, GLB, USD, STEP | STL, 3MF, STEP |
| AI workflow | Designed for agents | Standard Python |

## Limitations

- No native fillets or chamfers (mesh-based geometry)
- No loft or sweep operations
- V-groove approximated with rotated box cut (not trigonometric profile)
- Mounting slots simplified to round holes
- v0.1.0 — early-stage library with limited documentation

## Project Structure

```
src/vcad/
├── Cargo.toml          # Dependencies (vcad 0.1.0)
├── src/
│   ├── main.rs         # Entry point, builds all components
│   ├── peel_plate.rs   # Peel plate CSG
│   ├── vial_cradle.rs  # Vial cradle CSG
│   └── frame.rs        # Main frame CSG
```
