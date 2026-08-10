"""FastMCP application and tool definitions for visio-mcp.

Transport: stdio (standard for MCP clients such as Claude Code / Hermes).
On Windows with Visio installed the live COM engine is used; everywhere
else (or with VISIO_MCP_MOCK=1) a headless mock engine is used so the
server still boots and tools remain callable.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from fastmcp import FastMCP

from visio_mcp import __version__
from visio_mcp.config import get_config
from visio_mcp.pins import body_bounds as _body_bounds
from visio_mcp.pins import find_variant as _find_variant
from visio_mcp.pins import list_measured_masters as _list_measured_masters
from visio_mcp.pins import pin_point as _pin_point
from visio_mcp.pins import pin_names as _pin_names

app = FastMCP(
    name="VisioMCP",
    version=__version__,
    instructions=(
        "Draw circuit schematics and diagrams in Microsoft Visio. "
        "Workflow: new_document -> load_stencil -> drop_master -> draw_wire "
        "(use pin_point for exact pin coordinates) -> add_label -> add_junction "
        "-> export_page (png) -> iterate on the render."
    ),
)

_engine: Any = None


def _make_engine() -> Any:
    if os.environ.get("VISIO_MCP_MOCK", "0").strip().lower() in ("1", "true", "yes"):
        from visio_mcp.mock_engine import MockVisioEngine

        return MockVisioEngine()
    if sys.platform.startswith("win"):
        from visio_mcp.engine import VisioEngine

        return VisioEngine()
    from visio_mcp.mock_engine import MockVisioEngine

    return MockVisioEngine()


async def get_engine() -> Any:
    """Lazily created engine, auto-connected on first use."""
    global _engine
    if _engine is None:
        _engine = _make_engine()
        await _engine.connect()
    return _engine


# ===================================================================== #
# health
# ===================================================================== #
@app.tool()
async def health_check() -> dict:
    """Check server and Visio connection health."""
    try:
        eng = await get_engine()
        h = await eng.health()
        return {"status": "ok", **h, "version": __version__}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)}


# ===================================================================== #
# documents
# ===================================================================== #
@app.tool()
async def new_document(width: float = 16.0, height: float = 9.5,
                       units: str = "in", title: str = "") -> dict:
    """Create a new blank Visio document; page is scaled 1:1 so coordinates
    are inches. Returns the document name."""
    eng = await get_engine()
    name = await eng.new_document(width, height, units, title)
    return {"document": name}


@app.tool()
async def open_document(path: str) -> dict:
    """Open an existing Visio document (.vsdx)."""
    eng = await get_engine()
    return {"document": await eng.open_document(path)}


@app.tool()
async def save_document(path: str | None = None) -> dict:
    """Save the current document (optionally to a new path)."""
    eng = await get_engine()
    return {"saved": await eng.save_document(path)}


@app.tool()
async def close_document(save: bool = True) -> dict:
    """Close the current document."""
    eng = await get_engine()
    return {"closed": await eng.close_document(save)}


@app.tool()
async def list_pages() -> dict:
    """List pages in the current document."""
    eng = await get_engine()
    return {"pages": await eng.list_pages()}


@app.tool()
async def add_page(name: str) -> dict:
    """Add a new page and select it."""
    eng = await get_engine()
    return {"page": await eng.add_page(name)}


@app.tool()
async def select_page(name: str) -> dict:
    """Select a page by name."""
    eng = await get_engine()
    return {"selected": await eng.select_page(name)}


# ===================================================================== #
# stencils
# ===================================================================== #
@app.tool()
async def list_stencils(directory: str = "") -> dict:
    """List Visio stencil files (.vss/.vssx/.vssm) found in the configured
    stencil directories (VISIO_MCP_STENCIL_DIRS) or in `directory`."""
    import glob

    dirs = [directory] if directory else get_config().stencil_dirs
    found = []
    for d in dirs:
        for pat in ("*.vss", "*.vssx", "*.vssm"):
            found.extend(sorted(glob.glob(os.path.join(d, pat))))
    return {"stencils": found}


@app.tool()
async def load_stencil(path: str) -> dict:
    """Open a stencil file. If the file is locked by another Visio session,
    a temporary copy is opened instead. Returns a stencil key for drop_master."""
    eng = await get_engine()
    return {"stencil": await eng.load_stencil(path)}


@app.tool()
async def list_masters(stencil_path: str) -> dict:
    """List all masters (symbols) in a stencil file, with shape counts."""
    eng = await get_engine()
    return {"masters": await eng.list_masters(stencil_path)}


# ===================================================================== #
# shapes
# ===================================================================== #
@app.tool()
async def drop_master(stencil: str, master: str, x: float, y: float,
                      angle: float | None = None, flip_x: bool = False,
                      label: str = "", weight: str | None = None) -> dict:
    """Drop a stencil master at (x, y) in inches. Returns shape_id."""
    eng = await get_engine()
    sid = await eng.drop_master(stencil, master, x, y, angle, flip_x, label, weight)
    return {"shape_id": sid}


@app.tool()
async def draw_wire(points: list[list[float]], weight: str | None = None) -> dict:
    """Draw an orthogonal polyline through a list of [x, y] points (inches).
    Each consecutive pair becomes a straight segment. Returns shape ids."""
    eng = await get_engine()
    ids = await eng.draw_wire(points, weight)
    return {"shape_ids": ids, "segments": len(ids)}


@app.tool()
async def add_label(text: str, x: float, y: float, w: float = 0.55,
                    h: float = 0.24, size: str | None = None,
                    bold: bool = True, font: str | None = None) -> dict:
    """Add a centered text label (borderless, transparent) at (x, y)."""
    eng = await get_engine()
    sid = await eng.add_label(text, x, y, w, h, size, bold, font)
    return {"shape_id": sid}


@app.tool()
async def add_junction(x: float, y: float) -> dict:
    """Place a solid junction dot at (x, y) for >=3-wire nodes."""
    eng = await get_engine()
    sid = await eng.add_junction(x, y)
    return {"shape_id": sid}


@app.tool()
async def set_line_weight(shape_id: str, weight: str) -> dict:
    """Set LineWeight (e.g. '1.5 pt') on a shape and its sub-shapes."""
    eng = await get_engine()
    return {"updated": await eng.set_line_weight(shape_id, weight)}


@app.tool()
async def delete_shape(shape_id: str) -> dict:
    """Delete a shape by id."""
    eng = await get_engine()
    return {"deleted": await eng.delete_shape(shape_id)}


@app.tool()
async def find_shape(text: str) -> dict:
    """Find the first shape whose text contains `text`."""
    eng = await get_engine()
    sid = await eng.find_shape(text)
    return {"shape_id": sid, "found": sid is not None}


@app.tool()
async def list_shapes() -> dict:
    """List all shapes on the current page: id, master, text, position."""
    eng = await get_engine()
    return {"shapes": await eng.list_shapes()}


# ===================================================================== #
# export
# ===================================================================== #
@app.tool()
async def export_page(fmt: str, path: str) -> dict:
    """Export the current page to a file. fmt: png, jpg, gif, bmp, tif,
    svg, emf, pdf, vsdx. Returns the written path."""
    eng = await get_engine()
    return {"path": await eng.export_page(fmt, path)}


# ===================================================================== #
# measured pin geometry (Analog Circuit stencil)
# ===================================================================== #
@app.tool()
async def measured_pins() -> dict:
    """List stencil masters with measured pin geometry available."""
    out = {}
    for m in _list_measured_masters():
        out[m] = _pin_names(m)
    return {"masters": out}


@app.tool()
async def pin_point(master: str, x: float, y: float, pin: str,
                    angle: float | None = None, flip_x: bool = False) -> dict:
    """Absolute page coordinate (inches) of a symbol pin, based on measured
    geometry. Example: pin_point('NMOS1', 4.3, 6.0, 'gate') -> [4.049, 6.0].
    Use the result as the endpoint of draw_wire so wires land on pins."""
    pt = _pin_point(master, x, y, pin, angle, flip_x)
    if pt is None:
        return {"found": False, "reason": f"no pin '{pin}' for master {master}"}
    return {"found": True, "point": pt}


@app.tool()
async def symbol_bounds(master: str, x: float, y: float,
                        angle: float | None = None, flip_x: bool = False) -> dict:
    """Absolute ink bounding box of a symbol body (inches) for clearance
    checks — keep wires out of it."""
    b = _body_bounds(master, x, y, angle, flip_x)
    if b is None:
        return {"found": False}
    return {"found": True, "bounds": b}
