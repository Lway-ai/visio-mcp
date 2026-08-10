from __future__ import annotations

import pytest

from visio_mcp.mock_engine import MockVisioEngine


@pytest.fixture
async def engine():
    eng = MockVisioEngine()
    await eng.connect()
    yield eng
    await eng.close()


@pytest.fixture
async def doc(engine):
    await engine.new_document(16.0, 9.5, "in", "test")
    return engine
