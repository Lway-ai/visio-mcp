"""Server tool tests running against the mock engine (headless / CI)."""

from __future__ import annotations

import pytest

import visio_mcp.server as server
from visio_mcp.mock_engine import MockVisioEngine


@pytest.fixture
async def app_engine():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    server._engine = eng
    yield eng
    server._engine = None
    await eng.close()


async def test_health(app_engine):
    r = await server.health_check()
    assert r["status"] == "ok"
    assert r["connected"] is True


async def test_draw_wire_tool(app_engine):
    r = await server.draw_wire([[1, 1], [3, 1], [3, 4]])
    assert len(r["shape_ids"]) == 2


async def test_pin_point_tool():
    r = await server.pin_point("NMOS1", 4.3, 6.0, "gate")
    assert r["found"] is True
    assert r["point"] == [4.049, 6.0]
    r = await server.pin_point("NMOS1", 0, 0, "bogus")
    assert r["found"] is False


async def test_measured_pins_tool():
    r = await server.measured_pins()
    assert "NMOS1" in r["masters"]
    assert "gate" in r["masters"]["NMOS1"]


async def test_symbol_bounds_tool():
    r = await server.symbol_bounds("NMOS1", 12.3, 6.0, flip_x=True)
    assert r["found"] is True
    assert r["bounds"]["x_min"] == pytest.approx(12.033)


async def test_drop_master_tool(app_engine):
    key = await app_engine.load_stencil(r"C:\stencils\Analog Circuit.vss")
    r = await server.drop_master(key, "NMOS1", 4.3, 6.0, label="M1a")
    assert r["shape_id"] == "S1"
    shapes = await server.list_shapes()
    assert len(shapes["shapes"]) == 1


async def test_export_tool(app_engine):
    r = await server.export_page("png", r"C:\tmp\out.png")
    assert r["path"] == r"C:\tmp\out.png"
