"""Visio COM engine.

Design rules (hard-won in real automation sessions):

* All ``win32com`` access happens on ONE dedicated worker thread with
  ``pythoncom.CoInitialize()``; the public API is async and marshals calls
  there. COM objects must not be touched from other threads.
* Connect order: try ``GetActiveObject`` first (attach to a running Visio),
  fall back to ``Dispatch`` (launch a new instance). Under RDP the active
  object is often unavailable and Dispatch is required.
* ``AlertResponse = 1`` auto-answers modal dialogs so automation never hangs.
* Stencils that are open in another Visio UI session are LOCKED; we open a
  temporary copy instead and delete it afterwards.
* ``win32com`` is imported lazily so the package imports (and unit tests run)
  on non-Windows CI machines.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from visio_mcp.config import get_config


def _com_thread_init() -> None:
    import pythoncom  # noqa: PLC0415

    pythoncom.CoInitialize()


def _com_thread_exit() -> None:
    try:
        import pythoncom  # noqa: PLC0415

        pythoncom.CoUninitialize()
    except Exception:
        pass


def _temp_stencil_path(path: str) -> str:
    """Unique temp-copy path NEXT TO the original stencil.

    Files in %TEMP% are rejected by the Visio Trust Center file-block
    settings, and a per-pid name would collide when two different stencils
    are copied in the same process.
    """
    import hashlib

    h = hashlib.md5(os.path.abspath(path).lower().encode()).hexdigest()[:8]
    return os.path.join(
        os.path.dirname(os.path.abspath(path)),
        f"_visio_mcp_tmp_{os.getpid()}_{h}.vss",
    )


class VisioError(RuntimeError):
    """Raised for Visio-side failures (COM errors, missing masters...)."""


class VisioEngine:
    """Thin, robust COM gateway to Microsoft Visio."""

    def __init__(self) -> None:
        self._visio: Any = None
        self._doc: Any = None
        self._page: Any = None
        self._stencils: dict[str, Any] = {}  # logical name -> document
        self._tmp_stencils: list[str] = []  # temp copies to delete on close
        self._shape_names: dict[int, str] = {}  # shape id -> friendly name
        self._next_id: int = 1
        self.connected: bool = False
        self._launched: bool = False  # True only if we started this Visio
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="visio-com",
            initializer=_com_thread_init,
        )

    # ------------------------------------------------------------------ #
    # plumbing
    # ------------------------------------------------------------------ #
    async def _run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()

        def _wrapped() -> Any:
            try:
                if self._visio is not None:
                    self._visio.AlertResponse = 1
            except Exception:
                pass
            return fn(*args, **kwargs)

        return await loop.run_in_executor(self._executor, _wrapped)

    async def close(self) -> None:
        """Release COM resources; the launched Visio quits unless configured."""
        if self._doc is not None:
            try:
                await self._run(self._doc.Close)
            except Exception:
                pass
            self._doc = None
            self._page = None
        # close every stencil document we opened (leftover stencil tabs
        # litter the user's Visio and keep temp files locked)
        for key, st in list(self._stencils.items()):
            try:
                await self._run(st.Close)
            except Exception:
                pass
        self._stencils.clear()
        for path in self._tmp_stencils:
            try:
                os.remove(path)
            except OSError:
                pass
        self._tmp_stencils.clear()
        if self._visio is not None:
            # only quit the instance WE launched; never kill a user's Visio
            if self._launched and not get_config().visio_keep_alive:
                try:
                    await self._run(self._visio.Quit)
                except Exception:
                    pass
            self._visio = None
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, _com_thread_exit)
        except Exception:
            pass
        self._executor.shutdown(wait=True)
        self.connected = False

    # ------------------------------------------------------------------ #
    # connection / health
    # ------------------------------------------------------------------ #
    async def connect(self) -> bool:
        def _connect() -> bool:
            import win32com.client  # noqa: PLC0415

            if get_config().visio_attach:
                try:
                    self._visio = win32com.client.GetActiveObject("Visio.Application")
                    self._launched = False  # attached to an existing instance
                except Exception:
                    self._visio = win32com.client.Dispatch("Visio.Application")
                    self._launched = True  # we started this instance
            else:
                self._visio = win32com.client.Dispatch("Visio.Application")
                self._launched = True
            self._visio.Visible = bool(get_config().visio_visible)
            return True

        try:
            await self._run(_connect)
            self.connected = True
            return True
        except Exception as e:  # noqa: BLE001
            raise VisioError(f"Cannot connect to Visio: {e}") from e

    async def health(self) -> dict:
        if not self.connected or self._visio is None:
            return {"connected": False, "visio": "disconnected"}
        try:
            ver = await self._run(lambda: str(self._visio.Version))
            return {"connected": True, "visio": f"v{ver}"}
        except Exception:  # noqa: BLE001
            self.connected = False
            return {"connected": False, "visio": "error"}

    # ------------------------------------------------------------------ #
    # documents / pages
    # ------------------------------------------------------------------ #
    async def new_document(
        self,
        width: float = 16.0,
        height: float = 9.5,
        units: str = "in",
        title: str = "",
    ) -> str:
        def _new() -> str:
            doc = self._visio.Documents.Add("")
            self._doc = doc
            page = doc.Pages.Item(1)
            ps = page.PageSheet
            ps.CellsU("PageWidth").FormulaU = f"{width} {units}"
            ps.CellsU("PageHeight").FormulaU = f"{height} {units}"
            # 1:1 drawing scale makes page coordinates == inches
            ps.CellsU("PageScale").FormulaU = f"1 {units}"
            ps.CellsU("DrawingScale").FormulaU = f"1 {units}"
            self._page = page
            if title:
                try:
                    doc.Title = title
                except Exception:
                    pass
            return doc.FullName

        return await self._run(_new)

    async def open_document(self, path: str) -> str:
        def _open() -> str:
            self._doc = self._visio.Documents.Open(path)
            self._page = self._doc.Pages.Item(1)
            return path

        return await self._run(_open)

    async def save_document(self, path: str | None = None) -> str:
        def _save() -> str:
            if path:
                self._doc.SaveAs(path)
                return path
            self._doc.Save()
            return self._doc.FullName

        return await self._run(_save)

    async def close_document(self, save: bool = True) -> bool:
        def _close() -> bool:
            if save:
                try:
                    self._doc.Save()
                except Exception:
                    pass
            self._doc.Close()
            self._doc = None
            self._page = None
            return True

        return await self._run(_close)

    async def list_pages(self) -> list[str]:
        return await self._run(
            lambda: [p.Name for p in self._doc.Pages]
        )

    async def add_page(self, name: str) -> str:
        def _add() -> str:
            p = self._doc.Pages.Add()
            p.Name = name
            self._page = p
            return name

        return await self._run(_add)

    async def select_page(self, name: str) -> bool:
        def _sel() -> bool:
            for p in self._doc.Pages:
                if p.Name == name:
                    self._page = p
                    return True
            return False

        return await self._run(_sel)

    # ------------------------------------------------------------------ #
    # stencils (with lock workaround)
    # ------------------------------------------------------------------ #
    async def load_stencil(self, path: str) -> str:
        """Open a stencil document; returns a logical key usable by drop_master.

        If the file is locked by another Visio session (very common), copy it
        to a temp file and open the copy. The temp file is removed on close().
        """

        def _load() -> str:
            import win32com.client  # noqa: PLC0415

            opened = None
            used_tmp = False
            try:
                opened = self._visio.Documents.OpenEx(path, 64)
            except Exception:
                # locked or missing macro trust -> try a temporary copy.
                # The copy MUST live next to the original: files in %TEMP%
                # are rejected by the Trust Center file-block settings.
                tmp = os.path.join(
                    os.path.dirname(os.path.abspath(path)),
                    f"_visio_mcp_tmp_{os.getpid()}.vss",
                )
                shutil.copy2(path, tmp)
                opened = self._visio.Documents.OpenEx(tmp, 64)
                used_tmp = True
            key = f"stencil:{len(self._stencils) + 1}"
            self._stencils[key] = opened
            if used_tmp:
                self._tmp_stencils.append(tmp)
            return key

        return await self._run(_load)

    async def list_masters(self, path: str) -> list[dict]:
        """List masters of a stencil file without keeping it open."""

        def _list() -> list[dict]:
            import win32com.client  # noqa: PLC0415

            st = None
            tmp = None
            try:
                try:
                    st = self._visio.Documents.OpenEx(path, 64)
                except Exception:
                    tmp = os.path.join(
                        os.path.dirname(os.path.abspath(path)),
                        f"_visio_mcp_tmp_{os.getpid()}.vss",
                    )
                    shutil.copy2(path, tmp)
                    st = self._visio.Documents.OpenEx(tmp, 64)
                out = []
                for m in st.Masters:
                    try:
                        out.append(
                            {
                                "name": m.Name,
                                "name_u": m.NameU,
                                "shapes": m.Shapes.Count,
                            }
                        )
                    except Exception:
                        continue
                return out
            finally:
                if st is not None:
                    try:
                        st.Close()
                    except Exception:
                        pass
                if tmp and os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass

        return await self._run(_list)

    # ------------------------------------------------------------------ #
    # shapes
    # ------------------------------------------------------------------ #
    def _sid(self, shp: Any) -> str:
        try:
            key = int(shp.ID)
        except Exception:
            key = self._next_id + len(self._shape_names)
        name = self._shape_names.get(key)
        if name is None:
            name = f"S{key}"
            self._shape_names[key] = name
        return name

    async def drop_master(
        self,
        stencil_key: str,
        master: str,
        x: float,
        y: float,
        angle: float | None = None,
        flip_x: bool = False,
        label: str = "",
        weight: str | None = None,
    ) -> str:
        """Drop a stencil master at (x, y) in page inches. Returns shape id."""

        def _drop() -> str:
            doc = self._stencils[stencil_key]
            try:
                m = doc.Masters.ItemU(master)
            except Exception:
                m = doc.Masters.Item(master)
            shp = self._page.Drop(m, x, y)
            if angle is not None:
                shp.Cells("Angle").FormulaU = f"{angle} deg"
            if flip_x:
                shp.Cells("FlipX").FormulaU = "TRUE"
            if weight:
                _set_weight(shp, weight)
            if label:
                shp.Text = label
                try:
                    shp.Cells("Char.Size").FormulaU = get_config().label_size
                    shp.Cells("Char.Font").FormulaU = f'"{get_config().label_font}"'
                    shp.Cells("Char.Style").FormulaU = "1"
                    shp.Cells("Para.HorzAlign").FormulaU = "1"
                except Exception:
                    pass
            return self._sid(shp)

        return await self._run(_drop)

    async def draw_wire(
        self,
        points: list[list[float]],
        weight: str | None = None,
    ) -> list[str]:
        """Draw an orthogonal polyline through points. Returns shape ids."""

        def _draw() -> list[str]:
            w = weight or get_config().wire_weight
            ids = []
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                ln = self._page.DrawLine(x1, y1, x2, y2)
                ln.Cells("LineWeight").FormulaU = w
                ids.append(self._sid(ln))
            return ids

        return await self._run(_draw)

    async def add_label(
        self,
        text: str,
        x: float,
        y: float,
        w: float = 0.55,
        h: float = 0.24,
        size: str | None = None,
        bold: bool = True,
        font: str | None = None,
    ) -> str:
        """Add a borderless, fill-less, centered 2-D text label."""

        def _add() -> str:
            t = self._page.DrawRectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            t.Text = text
            t.Cells("FillPattern").FormulaU = "0"
            t.Cells("LinePattern").FormulaU = "0"
            t.Cells("Char.Size").FormulaU = size or get_config().label_size
            t.Cells("Char.Font").FormulaU = f'"{font or get_config().label_font}"'
            t.Cells("Char.Style").FormulaU = "1" if bold else "0"
            t.Cells("Para.HorzAlign").FormulaU = "1"
            return self._sid(t)

        return await self._run(_add)

    async def add_junction(self, x: float, y: float) -> str:
        """Place a junction dot at (x, y): stencil Point if available,
        otherwise a small filled circle. Returns shape id."""

        def _add() -> str:
            cfg = get_config()
            if cfg.dot_stencil:
                try:
                    key = f"dotstencil:{cfg.dot_stencil}"
                    if key not in self._stencils:
                        self._stencils[key] = self._visio.Documents.OpenEx(
                            cfg.dot_stencil, 64
                        )
                    shp = self._page.Drop(
                        self._stencils[key].Masters.ItemU(cfg.dot_master), x, y
                    )
                    return self._sid(shp)
                except Exception:
                    pass
            # fallback: filled circle
            shp = self._page.DrawOval(
                x - cfg.dot_fallback_radius_in,
                y - cfg.dot_fallback_radius_in,
                x + cfg.dot_fallback_radius_in,
                y + cfg.dot_fallback_radius_in,
            )
            shp.Cells("FillPattern").FormulaU = "1"
            shp.Cells("FillForegnd").FormulaU = "RGB(0,0,0)"
            shp.Cells("LineWeight").FormulaU = "0.75 pt"
            return self._sid(shp)

        return await self._run(_add)

    async def set_line_weight(self, shape_id: str, weight: str) -> bool:
        def _set() -> bool:
            shp = self._find_by_sid(shape_id)
            if shp is None:
                return False
            _set_weight(shp, weight)
            return True

        return await self._run(_set)

    async def delete_shape(self, shape_id: str) -> bool:
        def _del() -> bool:
            shp = self._find_by_sid(shape_id)
            if shp is None:
                return False
            shp.Delete()
            return True

        return await self._run(_del)

    async def find_shape(self, text: str) -> str | None:
        def _find() -> str | None:
            for shp in self._page.Shapes:
                try:
                    if text in shp.Text:
                        return self._sid(shp)
                except Exception:
                    continue
            return None

        return await self._run(_find)

    async def list_shapes(self) -> list[dict]:
        def _list() -> list[dict]:
            out = []
            for shp in self._page.Shapes:
                try:
                    master = None
                    try:
                        m = shp.Master
                        master = m.Name if m is not None else None
                    except Exception:
                        master = None
                    out.append(
                        {
                            "shape_id": self._sid(shp),
                            "name": shp.Name,
                            "master": master,
                            "text": str(shp.Text).strip()[:40],
                            "x": round(shp.Cells("PinX").Result("in"), 4),
                            "y": round(shp.Cells("PinY").Result("in"), 4),
                        }
                    )
                except Exception:
                    continue
            return out

        return await self._run(_list)

    def _find_by_sid(self, shape_id: str) -> Any:
        """Map a friendly shape id back to a live COM shape by matching the
        friendly-name registry, then by position in the shapes collection."""
        for key, name in self._shape_names.items():
            if name == shape_id:
                for shp in self._page.Shapes:
                    try:
                        if int(shp.ID) == key:
                            return shp
                    except Exception:
                        continue
        return None

    # ------------------------------------------------------------------ #
    # export
    # ------------------------------------------------------------------ #
    async def export_page(self, fmt: str, path: str, full_page: bool = True) -> str:
        """Export the current page. fmt: png/jpg/gif/bmp/tif/svg/emf/pdf/vsdx.

        With full_page=True (default) the export covers the whole page:
        Visio otherwise crops the output to the content bounding box, which
        breaks pixel-mapping. Invisible corner markers are added, the page is
        exported, and the markers are deleted again.
        """

        def _export() -> str:
            import win32com.client  # noqa: PLC0415

            markers: list[Any] = []
            if full_page:
                try:
                    w = self._page.PageSheet.CellsU("PageWidth").Result("in")
                    h = self._page.PageSheet.CellsU("PageHeight").Result("in")
                    for x0, y0 in ((0.0, 0.0), (w - 0.02, h - 0.02)):
                        # white-filled squares: they count as content geometry
                        # (so the export is not cropped) but render invisible
                        m = self._page.DrawRectangle(x0, y0, x0 + 0.02, y0 + 0.02)
                        m.Cells("LinePattern").FormulaU = "0"
                        m.Cells("FillPattern").FormulaU = "1"
                        m.Cells("FillForegnd").FormulaU = "RGB(255,255,255)"
                        markers.append(m)
                except Exception:
                    markers = []
            try:
                self._page.Export(path)
            except Exception:
                self._page.ExportAsFixedFormat(0, path, 1, 0)
            for m in markers:
                try:
                    m.Delete()
                except Exception:
                    pass
            return path

        return await self._run(_export)


def _set_weight(shp: Any, weight: str) -> None:
    """Recursively set LineWeight on a shape and its sub-shapes (groups)."""
    try:
        shp.Cells("LineWeight").FormulaU = weight
    except Exception:
        pass
    try:
        n = shp.Shapes.Count
    except Exception:
        n = 0
    for i in range(1, n + 1):
        _set_weight(shp.Shapes.Item(i), weight)
