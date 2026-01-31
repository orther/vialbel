#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check blender is installed
if ! command -v blender &> /dev/null; then
    echo "Error: Blender not found. Install from https://www.blender.org/download/"
    exit 1
fi

blender --background --python "$PROJECT_ROOT/src/blender/render_all.py" -- \
    --output "$PROJECT_ROOT/models/renders/" \
    "$@"
