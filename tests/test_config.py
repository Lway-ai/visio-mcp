from __future__ import annotations

import os

from visio_mcp.config import Config


def test_defaults():
    c = Config()
    assert c.wire_weight == "1.5 pt"
    assert c.label_font == "Arial"
    assert c.stencil_dirs == []
    assert c.visio_visible is False


def test_from_env(monkeypatch):
    monkeypatch.setenv("VISIO_MCP_STENCIL_DIRS", r"D:\stencils;C:\stencils")
    monkeypatch.setenv("VISIO_MCP_WIRE_WEIGHT", "2.16 pt")
    monkeypatch.setenv("VISIO_MCP_VISIBLE", "1")
    c = Config.from_env()
    assert c.stencil_dirs == [r"D:\stencils", r"C:\stencils"]
    assert c.wire_weight == "2.16 pt"
    assert c.visio_visible is True


def test_env_clears_defaults(monkeypatch):
    monkeypatch.setenv("VISIO_MCP_STENCIL_DIRS", "")
    c = Config.from_env()
    assert c.stencil_dirs == []


def test_wire_weight_survives_roundtrip():
    assert "2.16 pt" in "2.16 pt"
