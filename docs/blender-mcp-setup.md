# Blender MCP Setup

Connect Blender to Claude Code for AI-driven 3D visualization, assembly, and rendering.

## Prerequisites

- Blender 4.0+ (installed via `brew install --cask blender`)
- Python 3.10+ with `uvx` (`pip install uv` or `brew install uv`)

## 1. Add MCP Server to Claude Code

```bash
claude mcp add blender -- uvx blender-mcp
```

This registers the blender-mcp server so Claude can call Blender tools.

## 2. Install Blender Addon

1. Download `addon.py` from [blender-mcp](https://github.com/ahujasid/blender-mcp)
2. Open Blender → Edit → Preferences → Add-ons
3. Click "Install..." and select the downloaded `addon.py`
4. Enable the checkbox for "Interface: Blender MCP"

## 3. Connect

1. Open Blender
2. Press `N` to open the sidebar → find the "BlenderMCP" tab
3. Click "Connect to Claude"
4. Start a Claude Code session — Blender tools will be available

## Available Tools

| Tool | Description |
|------|-------------|
| `execute_blender_code` | Run arbitrary Python/bpy code in Blender |
| `get_scene_info` | Get current scene objects and properties |
| `get_object_info` | Get details about a specific object |
| `get_viewport_screenshot` | Capture current viewport as image |
| `set_material` | Apply materials to objects |
| `get_polyhaven_assets` | Browse PolyHaven material/model library |

## Workflow Scripts

Two scripts in `src/blender/` are designed to be executed via `execute_blender_code`:

- **`import_assembly.py`** — Imports all STL components at correct assembly positions with color-coded materials
- **`render_setup.py`** — Sets up camera, three-point lighting, and Cycles render settings for product photography

## Usage Example

From Claude Code, after Blender is connected:

1. Ask Claude to import the assembly: executes `import_assembly.py` via MCP
2. Ask Claude to set up rendering: executes `render_setup.py` via MCP
3. Ask Claude to capture a screenshot: uses `get_viewport_screenshot`
4. Ask Claude to modify materials or positions: uses `execute_blender_code`
