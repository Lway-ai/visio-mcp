from __future__ import annotations

import pytest

from visio_mcp.mock_engine import MockVisioEngine


async def test_lifecycle():
    eng = MockVisioEngine()
    assert await eng.connect() is True
    assert (await eng.health())["connected"] is True
    await eng.new_document(16.0, 9.5, "in", "t")
    await eng.close()
    assert eng.connected is False


async def test_draw_wire_creates_segments():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    ids = await eng.draw_wire([[1, 1], [2, 1], [2, 3]], "1.5 pt")
    assert len(ids) == 2
    shapes = await eng.list_shapes()
    assert len(shapes) == 2
    assert shapes[0]["kind"] == "wire"
    assert shapes[0]["weight"] == "1.5 pt"


async def test_drop_and_find():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    key = await eng.load_stencil(r"C:\stencils\Analog Circuit.vss")
    sid = await eng.drop_master(key, "NMOS1", 4.3, 6.0, label="M1a")
    found = await eng.find_shape("M1a")
    assert found == sid
    shapes = await eng.list_shapes()
    assert shapes[0]["master"] == "NMOS1"


async def test_delete():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    key = await eng.load_stencil("x")
    sid = await eng.drop_master(key, "Res1", 1, 1)
    assert await eng.delete_shape(sid) is True
    assert len(await eng.list_shapes()) == 0
    assert await eng.delete_shape(sid) is False


async def test_set_line_weight():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    key = await eng.load_stencil("x")
    sid = await eng.drop_master(key, "Ind2", 2, 2)
    assert await eng.set_line_weight(sid, "2.16 pt") is True
    shapes = await eng.list_shapes()
    assert shapes[0]["weight"] == "2.16 pt"


async def test_close_document_resets_page():
    eng = MockVisioEngine()
    await eng.connect()
    await eng.new_document()
    assert await eng.close_document() is True
    assert len(await eng.list_shapes()) == 0
