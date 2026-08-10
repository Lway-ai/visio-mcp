"""Two-stage differential 40 GHz LNA schematic — visio-mcp example.

Generates `TwoStage_Diff_LNA.vsdx` + PNG preview using the same public API
the MCP server exposes (engine + measured pin geometry). Run:

    python examples/lna_two_stage.py [output_dir] [stencil_dir]

Requires: Windows + Visio + the bundled stencils (stencils/ in the repo
root, or set VISIO_MCP_STENCIL_DIRS / pass the directory as 2nd arg).

Layout conventions (learned the hard way):
  * wires FIRST, components ON TOP -> series elements cover the wire
  * endpoints come from pin_point() (measured geometry) + 0.02..0.04 overlap
  * junction dots only at >=3-wire nodes
  * keep descents OUT of symbol body bounds (symbol_bounds)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# allow running from a checkout without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visio_mcp.engine import VisioEngine  # noqa: E402
from visio_mcp.pins import pin_point  # noqa: E402

WIRE = "2.16 pt"  # matches the component theme weight


def find_stencil(dirs: list[str], name: str) -> str:
    for d in dirs:
        p = Path(d) / name
        if p.exists():
            return str(p)
    raise FileNotFoundError(f"stencil not found: {name} in {dirs}")


async def main(out_dir: str, stencil_dir: str) -> None:
    analog = find_stencil([stencil_dir], "Analog Circuit.vss")
    rfic = find_stencil([stencil_dir], "RFIC_lib.vss")
    out = Path(out_dir) / "TwoStage_Diff_LNA.vsdx"
    out.parent.mkdir(parents=True, exist_ok=True)

    eng = VisioEngine()
    try:
        await eng.connect()
        await eng.new_document(16.0, 9.5, "in", "Two-Stage Diff LNA (40GHz)")
        sa = await eng.load_stencil(analog)
        sr = await eng.load_stencil(rfic)

        # ---- 1) wires first -------------------------------------------------
        def W(*pts):
            return eng.draw_wire([list(p) for p in pts], WIRE)

        await W((1.36, 5.06), (1.36, 5.5))                      # RF_in
        await W((1.36, 4.44), (1.36, 4.064))                    # balun-in gnd
        await W((1.85, 5.06), (1.85, 6.0), (2.646, 6.0))        # -> Lg1a
        await W((3.254, 6.0), (4.049, 6.0))                     # Lg1a -> M1a gate
        await W((1.85, 4.44), (3.396, 4.44))                    # -> Lg1b
        await W((4.004, 4.44), (7.157, 4.44), (7.157, 6.0))     # Lg1b -> M1b gate
        # VDD bus + stubs
        await W((3.5, 8.0), (13.5, 8.0))
        await W((13.2, 7.948), (13.2, 8.0))                     # vdd symbol
        for dx in (4.551, 6.660, 9.951, 12.060):
            await W((dx, 7.705), (dx, 8.0))
        # drains -> Ld -> VDD
        await W((4.551, 6.305), (4.551, 7.097))
        await W((6.660, 6.316), (6.660, 7.097))
        await W((9.951, 6.305), (9.951, 7.097))
        await W((12.060, 6.316), (12.060, 7.097))
        # interstage (y=6.65)
        await W((4.551, 6.65), (6.786, 6.65))                   # -> Cc1a
        await W((7.194, 6.65), (7.996, 6.65))                   # Cc1a -> Lg2a
        await W((8.604, 6.65), (9.449, 6.65), (9.449, 6.0))     # Lg2a -> M2a gate
        # Cc1b lane (y=4.75); descent at x=6.61 stays LEFT of M1b body
        await W((6.660, 6.316), (6.61, 6.316), (6.61, 4.75))
        await W((6.61, 4.75), (7.586, 4.75))
        await W((7.994, 4.75), (8.596, 4.75))
        await W((9.144, 4.75), (12.557, 4.75), (12.557, 6.0))   # -> M2b gate
        # outputs (descent at x=12.00 LEFT of M2b body)
        await W((9.951, 6.65), (14.95, 6.65), (14.95, 5.06))    # M2a -> balun
        await W((12.060, 6.316), (12.00, 6.316), (12.00, 4.44), (14.95, 4.44))
        await W((14.46, 5.06), (14.46, 5.5))                    # Vout
        await W((14.46, 4.44), (14.46, 4.064))                  # balun-out gnd
        # source buses + Ls tails
        await W((4.551, 5.70), (6.660, 5.70))
        await W((5.618, 5.70), (5.618, 5.205), (5.618, 4.596), (5.618, 4.036))
        await W((9.951, 5.70), (12.060, 5.70))
        await W((11.018, 5.70), (11.018, 5.205), (11.018, 4.596), (11.018, 4.036))
        # bias
        await W((2.75, 5.15), (3.541, 5.15))
        await W((4.049, 5.15), (4.049, 6.0))
        await W((6.15, 5.15), (6.649, 5.15))
        await W((7.157, 5.15), (7.157, 6.0))
        await W((8.5, 5.05), (8.941, 5.05))
        await W((9.449, 5.05), (9.449, 6.0))
        await W((11.6, 5.15), (12.049, 5.15))
        await W((12.557, 5.15), (12.557, 6.0))
        # C_dec
        await W((11.6, 8.0), (11.6, 7.805), (11.6, 7.396), (11.6, 7.064))

        # ---- 2) components --------------------------------------------------
        D = sa, "drop_master"
        await eng.drop_master(sa, "NMOS1", 4.3, 6.0)
        await eng.drop_master(sa, "NMOS1", 6.9, 6.0, flip_x=True)
        await eng.drop_master(sa, "NMOS1", 9.7, 6.0)
        await eng.drop_master(sa, "NMOS1", 12.3, 6.0, flip_x=True)
        await eng.drop_master(sa, "balun", 1.6, 4.75)
        await eng.drop_master(sa, "balun", 14.7, 4.75)
        await eng.drop_master(sa, "Ind2", 2.95, 6.0)            # Lg1a
        await eng.drop_master(sa, "Ind2", 3.7, 4.44)            # Lg1b
        await eng.drop_master(sa, "Res1", 3.805, 5.15)          # Rg1a
        await eng.drop_master(sa, "Res1", 6.913, 5.15)          # Rg1b
        for dx in (4.551, 6.660, 9.951, 12.060):                # Ld's (vertical)
            await eng.drop_master(sa, "Ind2", dx, 7.4, angle=0)
        for dx in (5.618, 11.018):                              # Ls's (vertical)
            await eng.drop_master(sa, "Ind2", dx, 4.9, angle=0)
        await eng.drop_master(sa, "Cap1", 7.0, 6.65, angle=90)  # Cc1a
        await eng.drop_master(sa, "Ind2", 8.3, 6.65)            # Lg2a
        await eng.drop_master(sa, "Cap1", 7.8, 4.75, angle=90)  # Cc1b
        await eng.drop_master(sa, "Ind2", 8.9, 4.75)            # Lg2b
        await eng.drop_master(sa, "Res1", 9.205, 5.05)          # Rg2a
        await eng.drop_master(sa, "Res1", 12.313, 5.15)         # Rg2b
        await eng.drop_master(sa, "vdd", 13.2, 8.05)
        await eng.drop_master(sa, "Cap1", 11.6, 7.6)            # C_dec
        for gx, gy in ((1.36, 3.9), (5.618, 4.2), (11.018, 4.2),
                       (11.59, 6.9), (14.46, 3.9)):
            await eng.drop_master(sa, "gnd", gx, gy)

        # ---- 3) junction dots (>=3-wire nodes) -----------------------------
        for x, y in (
            (4.049, 6.0), (7.157, 6.0), (9.449, 6.0), (12.557, 6.0),   # gates
            (4.049, 5.15), (7.157, 5.15), (9.449, 5.05), (12.557, 5.15),  # bias
            (4.551, 6.65), (6.660, 6.316), (9.951, 6.65), (12.060, 6.316),
        ):
            await eng.add_junction(x, y)

        # ---- 4) labels -----------------------------------------------------
        L = eng.add_label
        await L("Two-Stage Differential LNA (40 GHz)", 7.0, 9.0, 4.2, 0.35, "14pt")
        await L("Stage1/2: cascode-free CS with inductive degeneration | balun in/out",
                7.0, 8.6, 5.6, 0.24, "9pt")
        await L("RF_in", 1.15, 5.62)
        await L("Vout", 14.6, 5.62)
        await L("VDD", 13.7, 8.14)
        await L("Vb1", 2.45, 5.22)
        await L("Vb1", 5.9, 5.22)
        await L("Vb2", 8.2, 5.12)
        await L("Vb2", 11.35, 5.22)
        await L("Lg1a", 2.95, 6.38)
        await L("Lg1b", 3.7, 4.12)
        await L("Rg1a", 3.805, 4.75)
        await L("Rg1b", 6.913, 4.55)
        await L("Ld1a", 4.87, 7.42)
        await L("Ld1b", 6.98, 7.42)
        await L("Ld2a", 10.27, 7.42)
        await L("Ld2b", 12.38, 7.42)
        await L("Ls1", 5.95, 4.92)
        await L("Ls2", 11.35, 4.92)
        await L("Cc1a", 7.0, 7.05)
        await L("Lg2a", 8.3, 7.05)
        await L("Cc1b", 7.8, 4.35)
        await L("Lg2b", 8.9, 4.35)
        await L("Rg2a", 9.5, 4.55)
        await L("Rg2b", 12.313, 4.55)
        await L("C_dec", 11.15, 7.5)
        await L("M1a", 4.0, 6.45)
        await L("M1b", 6.15, 6.45)
        await L("M2a", 9.15, 6.42)
        await L("M2b", 12.25, 6.45)

        # ---- 5) save + export preview --------------------------------------
        await eng.save_document(str(out))
        await eng.export_page("png", str(out.with_suffix(".png")))
        print(f"written: {out}")
        print(f"preview: {out.with_suffix('.png')}")
    finally:
        await eng.close()


if __name__ == "__main__":
    import asyncio

    out_dir = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent)
    stencil_dir = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
        "VISIO_MCP_STENCIL_DIRS",
        str(Path(__file__).resolve().parent.parent / "stencils"),
    )
    asyncio.run(main(out_dir, stencil_dir))
