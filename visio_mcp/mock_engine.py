"""Headless in-memory engine used by unit tests and CI (no Visio, no Windows).

Mirrors the public API of :class:`visio_mcp.engine.VisioEngine` for the
parts the server tools rely on, so the same tool layer runs against both.
"""

from __future__ import annotations

from typing import Any


class MockVisioEngine:
    def __init__(self) -> None:
        self.connected = False
        self._doc: dict[str, Any] | None = None
        self._page: list[dict[str, Any]] = []
        self._masters: dict[str, list[str]] = {}
        self._next_id: int = 1

    # -- lifecycle ------------------------------------------------------ #
    async def connect(self) -> bool:
        self.connected = True
        return True

    async def close(self) -> None:
        self.connected = False
        self._doc = None
        self._page = []

    async def health(self) -> dict:
        return {"connected": self.connected, "visio": "mock"}

    # -- documents ------------------------------------------------------ #
    async def new_document(self, width=16.0, height=9.5, units="in", title="") -> str:
        self._doc = {"title": title, "width": width, "height": height}
        self._page = []
        return "mock://untitled"

    async def open_document(self, path: str) -> str:
        self._doc = {"path": path}
        self._page = []
        return path

    async def save_document(self, path: str | None = None) -> str:
        return path or "mock://untitled"

    async def close_document(self, save: bool = True) -> bool:
        self._doc = None
        self._page = []
        return True

    async def list_pages(self) -> list[str]:
        return ["Page-1"]

    async def add_page(self, name: str) -> str:
        return name

    async def select_page(self, name: str) -> bool:
        return name == "Page-1"

    # -- stencils ------------------------------------------------------- #
    async def load_stencil(self, path: str) -> str:
        key = f"stencil:{len(self._masters) + 1}"
        self._masters[key] = ["NMOS1", "PMOS1", "Res1", "Cap1", "Ind2", "gnd", "vdd"]
        return key

    async def list_masters(self, path: str) -> list[dict]:
        return [{"name": n, "name_u": n, "shapes": 1} for n in
                ["NMOS1", "PMOS1", "Res1", "Cap1", "Ind2", "gnd", "vdd"]]

    # -- shapes --------------------------------------------------------- #
    def _add_shape(self, kind: str, **kw: Any) -> str:
        sid = f"S{self._next_id}"
        self._next_id += 1
        self._page.append({"id": sid, "kind": kind, **kw})
        return sid

    async def drop_master(self, stencil_key, master, x, y, angle=None,
                          flip_x=False, label="", weight=None) -> str:
        return self._add_shape(
            "master", master=master, x=x, y=y, angle=angle,
            flip_x=flip_x, label=label, weight=weight,
        )

    async def draw_wire(self, points, weight=None) -> list[str]:
        ids = []
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            ids.append(self._add_shape(
                "wire", x1=x1, y1=y1, x2=x2, y2=y2, weight=weight,
            ))
        return ids

    async def add_label(self, text, x, y, w=0.55, h=0.24, size=None,
                        bold=True, font=None) -> str:
        return self._add_shape("label", text=text, x=x, y=y, w=w, h=h)

    async def add_junction(self, x, y) -> str:
        return self._add_shape("junction", x=x, y=y)

    async def set_line_weight(self, shape_id: str, weight: str) -> bool:
        for s in self._page:
            if s["id"] == shape_id:
                s["weight"] = weight
                return True
        return False

    async def delete_shape(self, shape_id: str) -> bool:
        for i, s in enumerate(self._page):
            if s["id"] == shape_id:
                del self._page[i]
                return True
        return False

    async def find_shape(self, text: str) -> str | None:
        for s in self._page:
            if text in str(s.get("label", "")):
                return s["id"]
        return None

    async def list_shapes(self) -> list[dict]:
        return [dict(s) for s in self._page]

    # -- export --------------------------------------------------------- #
    async def export_page(self, fmt: str, path: str) -> str:
        return path
