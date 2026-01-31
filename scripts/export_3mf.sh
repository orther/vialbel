#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# trimesh needs networkx and lxml for 3MF export
uvx --from trimesh --with numpy --with networkx --with lxml \
    python "$PROJECT_ROOT/src/blender/export_3mf.py" "$@"
