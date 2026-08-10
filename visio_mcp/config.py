"""Configuration for visio-mcp, driven entirely by environment variables.

No secrets, no personal paths in the repository: every machine-specific
value has a generic default and can be overridden per deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: list[str]) -> list[str]:
    v = os.environ.get(name)
    if not v:
        return default
    return [p.strip() for p in v.split(os.pathsep) if p.strip()]


@dataclass
class Config:
    """Resolved server configuration."""

    #: Directories to search for stencil files (.vss/.vssx). Semicolon-separated.
    stencil_dirs: list[str] = field(default_factory=list)

    #: Show the Visio application window (headless automation keeps it hidden).
    visio_visible: bool = False

    #: Attach to a running Visio instance (GetActiveObject) if available.
    #: Set 0 to always launch a dedicated instance — more deterministic when
    #: the user's interactive session is busy (e.g. stencils open in
    #: compatibility mode can make SaveAs flaky on the attached instance).
    visio_attach: bool = True

    #: Leave the launched Visio instance running after the server exits.
    visio_keep_alive: bool = False

    #: Default line weight for wires, in points (string form accepted by Visio).
    wire_weight: str = "1.5 pt"

    #: Default label font.
    label_font: str = "Arial"

    #: Default label size in points.
    label_size: str = "10pt"

    #: Default junction-dot stencil + master (RFIC Point is a 1 mm solid dot).
    dot_stencil: str = ""
    dot_master: str = "Point"

    #: Fallback junction style when the dot stencil is unavailable.
    dot_fallback_radius_in: float = 0.02

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            stencil_dirs=_env_list("VISIO_MCP_STENCIL_DIRS", []),
            visio_visible=_env_bool("VISIO_MCP_VISIBLE", False),
            visio_attach=_env_bool("VISIO_MCP_ATTACH", True),
            visio_keep_alive=_env_bool("VISIO_MCP_KEEP_ALIVE", False),
            wire_weight=os.environ.get("VISIO_MCP_WIRE_WEIGHT", "1.5 pt"),
            label_font=os.environ.get("VISIO_MCP_LABEL_FONT", "Arial"),
            label_size=os.environ.get("VISIO_MCP_LABEL_SIZE", "10pt"),
            dot_stencil=os.environ.get("VISIO_MCP_DOT_STENCIL", ""),
            dot_master=os.environ.get("VISIO_MCP_DOT_MASTER", "Point"),
        )


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
