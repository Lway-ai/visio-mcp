"""Validate the measured pin-geometry data and the pin_point math.

The reference values in this test are the ground truth measured from
rendered stencil masters (240 DPI pixel analysis).
"""

from __future__ import annotations

import pytest

from visio_mcp.pins import body_bounds, find_variant, list_measured_masters, pin_point


def test_all_masters_present():
    masters = list_measured_masters()
    for m in ("NMOS1", "Ind2", "Res1", "Cap1", "balun", "gnd", "vdd"):
        assert m in masters


def test_nmos1_gate_pin():
    # gate pin offset (-0.251, 0.0) -> absolute from drop point (4.3, 6.0)
    assert pin_point("NMOS1", 4.3, 6.0, "gate") == [4.049, 6.0]


def test_nmos1_drain_source():
    assert pin_point("NMOS1", 4.3, 6.0, "drain") == [4.551, 6.305]
    assert pin_point("NMOS1", 4.3, 6.0, "source") == [4.551, 5.697]


def test_nmos1_flipped_gate_on_right():
    pt = pin_point("NMOS1", 6.9, 6.0, "gate", flip_x=True)
    assert pt == [7.157, 6.0]


def test_ind2_horizontal_and_vertical():
    assert pin_point("Ind2", 2.95, 6.0, "left") == [2.647, 6.025]
    assert pin_point("Ind2", 2.95, 6.0, "right") == [3.255, 6.023]
    # vertical variant: angle=0 (master's baked 90 deg rotation removed)
    assert pin_point("Ind2", 4.551, 7.4, "top", angle=0) == [4.569, 7.705]
    assert pin_point("Ind2", 4.551, 7.4, "bottom", angle=0) == [4.569, 7.097]


def test_cap1_ports():
    # as-dropped: ports top/bottom
    assert pin_point("Cap1", 7.0, 6.65, "top") == [6.986, 6.855]
    assert pin_point("Cap1", 7.0, 6.65, "bottom") == [6.988, 6.446]
    # rotated 90: ports left/right (series capacitor on a horizontal lane)
    assert pin_point("Cap1", 7.0, 6.65, "left", angle=90) == [6.786, 6.65]
    assert pin_point("Cap1", 7.0, 6.65, "right", angle=90) == [7.194, 6.65]


def test_balun_coils():
    assert pin_point("balun", 1.6, 4.75, "right_coil_top") == [1.85, 5.06]
    assert pin_point("balun", 1.6, 4.75, "right_coil_bottom") == [1.85, 4.44]
    assert pin_point("balun", 1.6, 4.75, "left_coil_top") == [1.36, 5.06]


def test_unknown_pin_returns_none():
    assert pin_point("NMOS1", 0, 0, "no_such_pin") is None
    assert pin_point("NoSuchMaster", 0, 0, "gate") is None


def test_variant_matching():
    v = find_variant("NMOS1", angle=None, flip_x=True)
    assert v is not None and v["name"] == "flipped"
    v = find_variant("Ind2", angle=0, flip_x=False)
    assert v is not None and v["name"] == "vertical"


def test_body_bounds_clearance():
    # flipped NMOS1 at (12.3, 6.0): body occupies x 12.033..12.267
    b = body_bounds("NMOS1", 12.3, 6.0, flip_x=True)
    assert b is not None
    assert b["x_min"] == pytest.approx(12.033)
    assert b["x_max"] == pytest.approx(12.267)
    # a wire at x=12.00 is clear of the body
    assert 12.00 < b["x_min"]
    # a wire at x=12.10 would cross the body
    assert b["x_min"] < 12.10 < b["x_max"]
