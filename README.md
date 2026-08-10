# visio-mcp

MCP (Model Context Protocol) server for drawing **circuit schematics** and
diagrams in Microsoft Visio, driven by an LLM agent. MIT-licensed, 100%
original code — no parts copied from other Visio MCP projects.

![CI](https://img.shields.io/badge/CI-unit%20tests%20headless-green)

## Why

Drawing schematic netlists in Visio programmatically usually fails because
symbol pins live at unknown coordinates and wires end up floating next to
the symbols. This server ships **measured pin geometry** for the classic
*Analog Circuit* stencil: every master was rendered to a 240 DPI PNG and its
pins were located pixel-exact. `pin_point()` turns those offsets into exact
page coordinates, so wires land *on* the pins.

## Features

- **Live COM engine** — attaches to a running Visio (`GetActiveObject`) or
  launches a new instance (`Dispatch`); auto-answers modal dialogs; runs all
  COM on a single worker thread
- **Stencil lock workaround** — if a stencil is open in another Visio
  session (very common), a temporary copy is opened instead
- **Tools**: documents, pages, stencils, masters, shapes (drop / wire /
  label / junction / weight / delete / find / list), export (PNG/PDF/SVG/EMF…)
- **Measured pin geometry** for `Analog Circuit.vss` masters
  (NMOS1/PMOS1/Res1/Cap1/Ind2/balun/gnd/vdd) with orientation variants
- **Bundled stencils** — `stencils/` ships `Analog Circuit.vss`,
  `RFIC_lib.vss` and `RFsys_lib.vss` so the examples run out of the box
  (third-party academic symbols, see `stencils/README.md` for provenance)
- **Headless mock engine** — the same tool layer runs without Visio, so the
  test suite works on Linux CI
- **Example**: complete two-stage differential 40 GHz LNA schematic generator

## Requirements

| Requirement | Notes |
|---|---|
| Windows 10/11 | live mode |
| Microsoft Visio 2016+ | any edition |
| Python 3.11+ | |
| `stencils/` | bundled with the repo (`Analog Circuit.vss`, `RFIC_lib.vss`, `RFsys_lib.vss`); point `VISIO_MCP_STENCIL_DIRS` at it |

## Install

```bash
cd VISIO_MCP
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# stencils ship with the repo; point the server at them
export VISIO_MCP_STENCIL_DIRS="$PWD/stencils"
```

Probe Visio:

```bash
.venv\Scripts\python -m visio_mcp --check
```

## Run as an MCP server (stdio)

```bash
.venv\Scripts\visio-mcp
```

### Claude Code

```json
{
  "mcpServers": {
    "visio": {
      "command": "C:/path/to/your/stencils/VISIO_MCP/.venv/Scripts/python.exe",
      "args": ["-m", "visio_mcp"],
      "env": {
        "VISIO_MCP_STENCIL_DIRS": "C:/path/to/your/stencils"
      }
    }
  }
}
```

### Hermes Agent

```yaml
mcp_servers:
  visio:
    command: "C:/path/to/your/stencils/VISIO_MCP/.venv/Scripts/python.exe"
    args: ["-m", "visio_mcp"]
    env:
      VISIO_MCP_STENCIL_DIRS: "C:/path/to/your/stencils"
```

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `VISIO_MCP_STENCIL_DIRS` | (empty) | `;`-separated stencil search dirs for `list_stencils` |
| `VISIO_MCP_VISIBLE` | `0` | show the Visio window |
| `VISIO_MCP_ATTACH` | `1` | attach to a running Visio instance; `0` = always launch a dedicated instance (more deterministic) |
| `VISIO_MCP_KEEP_ALIVE` | `0` | keep the launched Visio instance after exit |
| `VISIO_MCP_WIRE_WEIGHT` | `1.5 pt` | default wire weight |
| `VISIO_MCP_LABEL_FONT` | `Arial` | default label font |
| `VISIO_MCP_LABEL_SIZE` | `10pt` | default label size |
| `VISIO_MCP_DOT_STENCIL` | (empty) | junction-dot stencil (e.g. RFIC_lib.vss) |
| `VISIO_MCP_DOT_MASTER` | `Point` | junction-dot master name |
| `VISIO_MCP_MOCK` | `0` | force the headless mock engine |

## Tools

| Tool | Description |
|---|---|
| `health_check` | server + Visio connection status |
| `new_document` / `open_document` / `save_document` / `close_document` | document lifecycle (1:1 inch page) |
| `list_pages` / `add_page` / `select_page` | page control |
| `list_stencils` / `load_stencil` / `list_masters` | stencil + master discovery |
| `drop_master` | drop a symbol (angle, flip, label, weight) |
| `draw_wire` | orthogonal polyline, uniform weight |
| `add_label` | centered borderless text (Arial bold) |
| `add_junction` | solid junction dot (Point master or filled circle) |
| `set_line_weight` / `delete_shape` / `find_shape` / `list_shapes` | shape management |
| `export_page` | PNG / JPG / SVG / EMF / PDF / VSDX |
| `measured_pins` / `pin_point` / `symbol_bounds` | measured pin geometry & clearance |

## Drawing recipe (agent workflow)

1. `new_document(16, 9.5)` — coordinates are inches
2. `load_stencil("…/Analog Circuit.vss")` — get a stencil key
3. `drop_master(key, "NMOS1", x, y, flip_x=…)` for every symbol
4. `pin_point("NMOS1", x, y, "gate")` — exact pin coordinate
5. `draw_wire([[..], pin_point, ..])` — wires **first**, components on top
   (series elements cover the wire; use `symbol_bounds` to keep descents
   out of bodies)
6. `add_junction` at ≥3-wire nodes, `add_label` for names
7. `export_page("png", "out.png")` — inspect, iterate

## Pitfalls

- **Do not keep the output .vsdx open in Visio while regenerating it** —
  SaveAs then fails with an "invalid DOS handle" error. Close the file first
  (or write to a new path).
- **Temporary stencil copies must live next to the original stencil** —
  files in %TEMP% are rejected by the Visio Trust Center file-block settings.
- **If a user's interactive Visio session feels flaky** (stencils open in
  compatibility mode, unsaved docs, ...), set `VISIO_MCP_ATTACH=0` so the
  server drives its own dedicated instance.

## Measured pin data

`visio_mcp/data/pins_analog_circuit.json` — offsets in inches relative to the
drop point (y-up page coordinates), measured by PNG-render + pixel analysis.
Variants encode rotations (`angle`) and mirrors (`flip_x`). Verified against
the two-stage LNA example (all 21 connections pixel-checked).

## Project layout

```
visio_mcp/
  engine.py        live COM engine (single worker thread, lazy win32com)
  mock_engine.py   headless engine for CI
  server.py        FastMCP app + tools
  pins.py          measured-geometry helpers
  data/pins_analog_circuit.json
stencils/           bundled Visio stencils (Analog Circuit / RFIC_lib / RFsys_lib)
examples/lna_two_stage.py   two-stage diff LNA schematic generator
tests/                      unit tests (headless)
```

## License

MIT — the code, the measured pin-geometry JSON, and this documentation are
original work of this project's author. The bundled stencils in `stencils/`
(`Analog Circuit.vss`, `RFIC_lib.vss`, `RFsys_lib.vss`) are **third-party
academic symbols** (originally created at Fudan University) and are **not**
covered by this project's MIT license — see `stencils/README.md` for their
provenance and terms.
