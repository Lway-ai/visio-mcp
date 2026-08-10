"""MCP stdio smoke test: spawn the server, call tools over the MCP protocol.

Run:  .venv/Scripts/python.exe scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports.stdio import PythonStdioTransport

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"


async def main() -> None:
    async with Client(
        PythonStdioTransport(script_path=str(ROOT / "visio_mcp" / "__main__.py"), cwd=str(ROOT)),
    ) as client:
        tools = await client.list_tools()
        print(f"tools discovered: {len(tools)}")
        names = sorted(t.name for t in tools)
        assert "draw_wire" in names and "pin_point" in names and "drop_master" in names
        print("  " + ", ".join(names[:8]) + " ...")

        h = await client.call_tool("health_check", {})
        print("health:", h)

        r = await client.call_tool("pin_point", {"master": "NMOS1", "x": 4.3, "y": 6.0, "pin": "gate"})
        print("pin_point:", r)

        r = await client.call_tool("new_document", {"width": 16, "height": 9.5})
        print("new_document:", r)

        r = await client.call_tool("draw_wire", {"points": [[1, 1], [2, 1], [2, 3]], "weight": "1.5 pt"})
        print("draw_wire:", r)

        r = await client.call_tool("add_label", {"text": "SmokeTest", "x": 1.5, "y": 3.5})
        print("add_label:", r)

        r = await client.call_tool("add_junction", {"x": 1.0, "y": 1.0})
        print("add_junction:", r)

        shapes = await client.call_tool("list_shapes", {})
        print("list_shapes count:", len(shapes.content[0].text) if shapes.content else 0)

        out = Path(tempfile.gettempdir()) / f"visio_mcp_smoke_{os.getpid()}.vsdx"
        # unique path: a previous run's output left open in a Visio instance
        # would lock the file and make SaveAs fail with "invalid DOS handle"
        if out.exists():
            out.unlink()
        r = await client.call_tool("save_document", {"path": str(out)})
        print("save_document:", r)
        r = await client.call_tool("export_page", {"fmt": "png", "path": str(out.with_suffix(".png"))})
        print("export_page:", r)
        assert out.exists() and out.with_suffix(".png").exists()
        print("SMOKE OK ->", out)


if __name__ == "__main__":
    asyncio.run(main())
