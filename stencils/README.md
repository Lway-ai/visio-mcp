# Bundled stencils — provenance and license

This directory ships three Visio stencils so the examples and the MCP server
work out of the box:

| File | Masters | Origin (from file metadata) |
|---|---|---|
| `Analog Circuit.vss` | 57 (NMOS1/PMOS1/Ind2/Cap1/Res1/balun/gnd/vdd/…) | Author: yfhan (Simplified-Chinese codepage) |
| `RFIC_lib.vss` | 46 (NPN/PNP/Transformer/PAD/Point/Varactor/…) | Author: Administrator, Company: Fudan University, last saved 2013-10-29 |
| `RFsys_lib.vss` | 25 (Antenna/LNA/Mixer/LO/ADC/DAC/Opamp/…) | Author: Zhangwen Tang, Company: Fudan University, last saved 2008-02-18 |

These are **third-party academic symbols** widely used for RF/analog circuit
teaching and research (originally created at Fudan University). They are
**NOT** original work of this repository's author and are **NOT covered by the
MIT license** of this project.

- They are bundled here as-is ("AS IS", no warranty, no support) for
  convenience.
- Copyright remains with the original authors / institution.
- If you are not entitled to redistribute them (e.g. you received them under
  a stricter agreement), remove this directory before publishing or
  distributing the repository.
- The measured pin geometry in `visio_mcp/data/pins_analog_circuit.json`
  was derived from the `Analog Circuit.vss` masters by rendering them to PNG
  and analyzing pixels. The JSON itself (offsets in inches) is original
  measurement data of this project and is MIT-licensed.

Point `VISIO_MCP_STENCIL_DIRS` at this directory (or the repo root) to use
them, e.g.:

```bash
export VISIO_MCP_STENCIL_DIRS="$PWD/stencils"
```
