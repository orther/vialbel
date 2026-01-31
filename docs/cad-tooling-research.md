# Programmatic CAD Tooling Research

**Date:** 2026-01-29
**Purpose:** Evaluate Python-scriptable, headless CAD tools for generating 3D-printable mechanical parts (peel plates, V-block cradles, spring-loaded tension arms, frames with heat-set insert recesses) targeting ASA on a Bambu Lab P1S.

**Key requirements:** Fillets/chamfers (2mm radius edges), clean STL/3MF export, fully headless operation, parametric design.

---

## Tool Comparison Matrix

| Criteria (1-5)                  | CadQuery | Build123d | SolidPython2 | OpenSCAD | FreeCAD (Python) |
|---------------------------------|----------|-----------|--------------|----------|------------------|
| Headless/CLI reliability        | 5        | 5         | 4            | 4        | 2                |
| Parametric design support       | 5        | 5         | 4            | 4        | 4                |
| STL/3MF export                  | 5        | 5         | 3            | 3        | 4                |
| Fillets, chamfers, smooth curves| 5        | 5         | 2            | 2        | 5                |
| Boolean operations              | 5        | 5         | 4            | 4        | 5                |
| Documentation quality           | 4        | 4         | 3            | 4        | 3                |
| Ease of installation (pip)      | 4        | 4         | 5            | 3        | 1                |
| Community/maintenance activity  | 4        | 4         | 2            | 4        | 5                |
| **Total**                       | **37**   | **37**    | **27**       | **28**   | **29**           |

---

## Detailed Evaluation

### 1. CadQuery

**GitHub:** https://github.com/CadQuery/cadquery
**Install:** `pip install cadquery` (Python 3.9-3.12, 3.13 partial)
**Kernel:** Open CASCADE Technology (OCCT) via OCP bindings

**Pros:**
- Built from the ground up for headless, scriptable CAD -- no GUI dependency whatsoever
- Full BREP kernel (OCCT) provides native, high-quality fillets and chamfers on any edge
- Exports STL, STEP, 3MF, DXF, VRML, AMF natively
- Fluent/chained API for building parametric models
- Strong ecosystem: cq-kit, cqparts, CQ-editor for optional visualization
- Active development; pip-installable with binary wheels on all major platforms
- Tolerance control on STL tessellation for print quality tuning

**Cons:**
- Fluent/method-chaining API can be hard to debug -- stack traces are opaque
- String-based selectors (e.g., `">Z"`) lack IDE autocomplete
- cadquery-ocp wheels are large (~200MB) and only cover specific Python versions
- conda was historically the recommended install path; pip support is newer and occasionally has dependency issues

**Best for:** Production headless workflows, CI/CD pipelines, batch part generation

---

### 2. Build123d

**GitHub:** https://github.com/gumyr/build123d
**Install:** `pip install build123d` (Python 3.10-3.13)
**Kernel:** OCCT via the same OCP bindings as CadQuery

**Pros:**
- More Pythonic API than CadQuery -- uses context managers instead of method chaining
- Dual modeling: both builder-pattern (feature stack) and algebra-mode (CSG tree), combinable
- Enums replace string selectors -- full IDE autocomplete and type checking
- Native fillets/chamfers with intuitive edge selection (`group_by`, `filter_by`)
- STL and 3MF export via `Mesher` class with tolerance control
- Extensible via standard Python classes (no monkey-patching)
- Interoperable with CadQuery objects (shared OCP wrapper)
- Actively maintained by gumyr (original CadQuery contributor)

**Cons:**
- Younger project -- some APIs may still change
- Smaller community and fewer third-party examples than CadQuery
- Same large OCP binary wheel dependency
- Documentation is good but less battle-tested than CadQuery's

**Best for:** New projects where a modern, Pythonic API and strong IDE support matter

---

### 3. SolidPython2

**GitHub:** https://github.com/SolidCode/SolidPython
**Install:** `pip install solidpython2` (Python 3.7+)
**Kernel:** Generates OpenSCAD code; requires OpenSCAD installed for rendering

**Pros:**
- Trivial pip install (pure Python, no binary dependencies)
- Full Python language features for parametric design (loops, functions, classes)
- BOSL2 library integration for advanced shapes
- Lightweight -- just generates `.scad` files

**Cons:**
- **No native fillets/chamfers** -- inherits all of OpenSCAD's CGAL limitations
- Fillets require Minkowski sum (extremely slow on complex geometry) or manual construction
- Requires OpenSCAD as an external runtime dependency for STL export
- Only mesh-based export (STL); no STEP or native 3MF
- Low download numbers (188/week); beta status
- Two-step workflow: generate .scad, then invoke OpenSCAD to render
- OpenSCAD rendering can be very slow for complex models

**Best for:** Simple parts where OpenSCAD familiarity exists; not suitable for parts requiring fillets

---

### 4. OpenSCAD (Direct)

**Website:** https://openscad.org
**Install:** System package or download; no pip install
**Kernel:** CGAL (CSG-based)

**Pros:**
- Mature, well-documented scripting language purpose-built for parametric CAD
- Headless CLI mode: `openscad -o output.stl input.scad`
- Large community, many existing libraries (BOSL2, NopSCADlib, etc.)
- Customizer for parametric variants
- Good for simple mechanical parts and enclosures

**Cons:**
- **No native fillet or chamfer operations** -- fundamental limitation of CSG/CGAL kernel
- Workarounds (Minkowski sum) are impractical for complex geometry (hours/days to compute)
- Not Python -- custom language with limited programming constructs
- STL export only (no STEP, limited 3MF via external tools)
- Cannot represent smooth curves natively; everything is mesh-approximated from the start
- 2mm radius edge fillets on complex parts would be extremely difficult

**Best for:** Simple box/cylinder CSG parts; poor fit for parts needing fillets

---

### 5. FreeCAD (Python Scripting)

**GitHub:** https://github.com/FreeCAD/FreeCAD
**Install:** System install required; no pip install of the CAD kernel
**Kernel:** OCCT (same as CadQuery/Build123d)

**Pros:**
- Full professional CAD kernel with excellent fillet/chamfer/boolean support
- Massive feature set: PartDesign, Part, Draft, Sketcher, FEM, CAM
- Large, active community; well-funded open source project
- Can theoretically do anything a commercial CAD package can

**Cons:**
- **Headless operation is unreliable** -- many modules silently depend on GUI components
- May require `xvfb` (virtual framebuffer) on Linux for headless operation
- No pip install -- requires system FreeCAD installation and manual Python path configuration
- API is verbose and not Pythonic; documentation for scripting is scattered
- Different Python version between FreeCAD's bundled interpreter and your venv causes import errors
- Fragile setup for CI/CD or automated pipelines

**Best for:** Interactive CAD work with Python macros; poor fit for headless automation

---

## MCP Server Findings

Several MCP (Model Context Protocol) servers exist for CAD integration with AI assistants:

### FreeCAD MCP Servers

| Server | GitHub | Notes |
|--------|--------|-------|
| **contextform/freecad-mcp** | https://github.com/contextform/freecad-mcp | Most feature-rich: 13 PartDesign ops (Pad, Fillet, Chamfer, Holes, Patterns) + 18 Part ops (Booleans, Transforms). Open source. |
| **neka-nat/freecad-mcp** | https://github.com/neka-nat/freecad-mcp | Control FreeCAD from Claude Desktop via uv. Simpler scope. |
| **lucygoodchild/freecad-mcp-server** | https://github.com/lucygoodchild/freecad-mcp-server | Basic geometry creation, booleans, document management. Cross-platform. |
| **bonninr/freecad_mcp** | https://github.com/bonninr/freecad_mcp | Claude/Cursor integration for prompt-assisted CAD design. |
| **jango-blockchained/mcp-freecad** | https://github.com/jango-blockchained/mcp-freecad | Multiple AI provider support, robust connection methods. |

### OpenSCAD MCP Servers

| Server | GitHub | Notes |
|--------|--------|-------|
| **quellant/openscad-mcp** | https://github.com/quellant/openscad-mcp | Production-ready FastMCP server for OpenSCAD rendering. v1.0.0 (Aug 2025). |
| **jhacksman/OpenSCAD-MCP-Server** | https://github.com/jhacksman/OpenSCAD-MCP-Server | Text/image to 3D model generation. Multi-view reconstruction. 102 stars. |

### No CadQuery/Build123d MCP Servers Found

There are currently no MCP servers specifically for CadQuery or Build123d. However, since both are pure Python libraries, an MCP server wrapping them would be straightforward to build -- the LLM would generate CadQuery/Build123d Python code directly, which is already a well-documented pattern ("Text-to-CadQuery").

---

## Recommendation

### Primary: **Build123d**

Build123d is the strongest choice for this use case:

1. **Fillets/chamfers are first-class operations** -- 2mm radius edges on peel plates, smooth V-block cradle profiles, and rounded frame features are trivial with `fillet()` and `chamfer()` on selected edges.

2. **Fully headless** -- pure Python library, no GUI dependency, no xvfb hacks. Works in scripts, CI/CD, and automated pipelines.

3. **Clean export** -- native STL and 3MF export with tessellation tolerance control. 3MF is preferred for Bambu Lab P1S (Bambu Studio natively uses 3MF).

4. **Modern Pythonic API** -- context managers, enums, type hints, and IDE autocomplete make parametric design readable and maintainable. Dual builder/algebra modes suit different part design styles.

5. **Same OCCT kernel** as CadQuery and FreeCAD -- no compromises on geometric quality.

6. **pip installable** -- `pip install build123d` with binary wheels.

### Fallback: **CadQuery**

If Build123d's newer API causes issues or a specific feature is missing, CadQuery is a drop-in alternative sharing the same OCCT kernel. The ecosystem is larger and more battle-tested. Objects can be transferred between the two libraries.

### Not Recommended for This Use Case

- **SolidPython2/OpenSCAD** -- The lack of native fillets makes 2mm radius edges on complex parts impractical. The CGAL kernel cannot handle the geometry requirements.
- **FreeCAD scripting** -- Headless operation is too fragile for reliable automated part generation.

### MCP Integration Path

No existing MCP server covers CadQuery/Build123d, but building one would be straightforward since the tools are already Python-native. For immediate MCP-assisted CAD, **contextform/freecad-mcp** is the most capable option, though it requires a FreeCAD installation. The recommended approach is to use Build123d directly in Python scripts, potentially wrapping it in a custom MCP server later if conversational CAD design is desired.
