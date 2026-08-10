"""Pin-geometry helpers built on the measured stencil data.

The JSON file ``data/pins_analog_circuit.json`` holds pin offsets measured by
rendering each stencil master to a high-DPI PNG and analyzing ink pixels.
These helpers turn (master, variant, drop point) into exact absolute pin
coordinates in page inches — the key to drawing wires that actually connect.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA = Path(__file__).parent / "data" / "pins_analog_circuit.json"


def _load() -> dict[str, Any]:
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


_PINS: dict[str, Any] | None = None


def get_pins_db() -> dict[str, Any]:
    global _PINS
    if _PINS is None:
        _PINS = _load()
    return _PINS


def list_measured_masters() -> list[str]:
    return sorted(get_pins_db()["masters"].keys())


def find_variant(master: str, angle: float | None = None,
                 flip_x: bool = False) -> dict[str, Any] | None:
    """Return the measured variant matching the requested orientation.

    Matching is exact on (angle, flip_x); if no exact match, return the
    first variant with the same flip_x (orientation-agnostic fallback).
    """
    db = get_pins_db()
    masters = db.get("masters", {})
    entry = masters.get(master)
    if not entry:
        return None
    variants = entry.get("variants", [])
    for v in variants:
        if v.get("angle") == angle and v.get("flip_x") == flip_x:
            return v
    for v in variants:
        if v.get("flip_x") == flip_x:
            return v
    return None


def pin_point(master: str, x: float, y: float, pin: str,
              angle: float | None = None, flip_x: bool = False) -> list[float] | None:
    """Absolute page coordinates of a master's pin in inches.

    Example: pin_point("NMOS1", 4.3, 6.0, "gate") -> [4.049, 6.0]
    """
    v = find_variant(master, angle, flip_x)
    if v is None or pin not in v.get("pins", {}):
        return None
    dx, dy = v["pins"][pin]
    return [round(x + dx, 4), round(y + dy, 4)]


def pin_names(master: str, angle: float | None = None,
              flip_x: bool = False) -> list[str]:
    v = find_variant(master, angle, flip_x)
    if v is None:
        return []
    return list(v.get("pins", {}).keys())


def body_bounds(master: str, x: float, y: float,
                angle: float | None = None, flip_x: bool = False
                ) -> dict[str, float] | None:
    """Absolute ink bounding box of the symbol body (clearance checks)."""
    v = find_variant(master, angle, flip_x)
    if v is None or "body" not in v:
        return None
    b = v["body"]
    return {
        "x_min": round(x + b["x_min"], 4),
        "x_max": round(x + b["x_max"], 4),
        "y_min": round(y + b["y_min"], 4),
        "y_max": round(y + b["y_max"], 4),
    }
