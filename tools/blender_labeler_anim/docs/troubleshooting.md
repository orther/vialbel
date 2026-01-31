# Troubleshooting

## Common Issues

### "No module named 'core'"
Ensure the script adds the parent directory to sys.path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

### GPU rendering fails in headless mode
- Check `blender --version` supports Metal (macOS) or OptiX/CUDA (Linux/Windows)
- Fallback: use `--engine BLENDER_EEVEE_NEXT` or set Cycles to CPU

### Geometry Nodes not applying
- Ensure the modifier's `node_group` is set before accessing inputs
- Check that socket types match (Float vs Vector, etc.)

### Driver not updating
- After adding drivers programmatically, call:
  ```python
  bpy.context.view_layer.update()
  bpy.app.handlers.depsgraph_update_post.clear()  # if stuck
  ```

### Blender 5.0 API changes
- `bpy.data.node_groups.new()` type is `'GeometryNodeTree'` (not `'GEOMETRY_NODES'`)
- Interface sockets use `tree.interface.new_socket()` instead of `tree.inputs.new()`
- Action/fcurve API has changed; prefer drivers over keyframed actions where possible

### ffmpeg not found
- Install via `brew install ffmpeg` (macOS) or package manager
- Or skip MP4 encoding: omit `--encode-mp4` flag
