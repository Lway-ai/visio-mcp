# Examples

## lna_two_stage.py

Two-stage differential 40 GHz LNA schematic generated entirely through the
visio-mcp public API (the same API the MCP server exposes as tools).

```
python examples/lna_two_stage.py [output_dir] [stencil_dir]
```

- `output_dir` — where `TwoStage_Diff_LNA.vsdx` + `.png` are written (default: `examples/`)
- `stencil_dir` — directory containing `Analog Circuit.vss` and `RFIC_lib.vss`
  (default: the bundled `stencils/` dir in the repo root; override with env
  `VISIO_MCP_STENCIL_DIRS` or the 2nd argument)

What it demonstrates:

1. `VisioEngine` lifecycle: `connect -> new_document -> load_stencil -> draw`
2. draw wires FIRST, components on top (series elements cover the wire)
3. wire endpoints computed with `pin_point()` — the measured pin geometry
   from `visio_mcp/data/pins_analog_circuit.json`
4. junction dots via `add_junction` (RFIC Point master)
5. labels via `add_label` (borderless, centered, Arial bold)
6. export to PNG for visual verification

The layout constants embed the routing rules (keep descents out of symbol
bodies, dots only at >=3-wire nodes, wire weight matching the component
theme weight).
