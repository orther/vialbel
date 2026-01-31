#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/models/renders/animation"

mkdir -p "$OUTPUT_DIR"

echo "Rendering animation frames..."
blender --background --python "$PROJECT_ROOT/src/blender/animate_demo.py" -- \
    --output "$OUTPUT_DIR/" "$@"

# Combine PNG sequence to MP4
if command -v ffmpeg &>/dev/null; then
    echo "Combining frames to MP4..."
    ffmpeg -y -framerate 30 -i "$OUTPUT_DIR/frame_%04d.png" \
        -c:v libx264 -crf 18 -pix_fmt yuv420p \
        "$OUTPUT_DIR/demo_animation.mp4"
    echo "Animation saved to $OUTPUT_DIR/demo_animation.mp4"
else
    echo "ffmpeg not found — PNG frames saved to $OUTPUT_DIR/"
    echo "Install ffmpeg and run: ffmpeg -y -framerate 30 -i '$OUTPUT_DIR/frame_%04d.png' -c:v libx264 -crf 18 -pix_fmt yuv420p '$OUTPUT_DIR/demo_animation.mp4'"
fi
