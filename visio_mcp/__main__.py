"""CLI entry point: ``python -m visio_mcp`` starts the stdio MCP server.

Extra commands:
    python -m visio_mcp --check     probe Visio availability and exit
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def _check() -> int:
    if not sys.platform.startswith("win"):
        print("visio-mcp: not on Windows; live Visio unavailable (mock engine will be used)")
        return 0
    try:
        import win32com.client  # noqa: PLC0415
    except ImportError:
        print("visio-mcp: pywin32 not installed")
        return 1
    try:
        app = win32com.client.GetActiveObject("Visio.Application")
        print(f"visio-mcp: Visio running (v{app.Version})")
    except Exception:
        try:
            app = win32com.client.Dispatch("Visio.Application")
            print(f"visio-mcp: Visio launchable (v{app.Version}); quitting probe instance")
            app.Quit()
        except Exception as e:  # noqa: BLE001
            print(f"visio-mcp: cannot reach Visio: {e}")
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="visio-mcp")
    parser.add_argument("--check", action="store_true", help="probe Visio and exit")
    args = parser.parse_args()
    if args.check:
        return _check()
    from visio_mcp.server import app

    app.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
