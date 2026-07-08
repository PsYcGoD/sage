"""Agentic loop configuration — loads from sage.toml or ~/.sage/config.toml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgenticConfig:
    """Configuration for the agentic loop."""
    autonomy: str = "suggest"
    max_retries: int = 3
    auto_fix_patterns: list[str] = field(default_factory=lambda: [
        "missing_module", "permission", "port_in_use", "command_not_found",
    ])
    never_auto_fix: list[str] = field(default_factory=lambda: [
        "git_force_push", "rm_rf", "drop_table", "format_disk",
    ])
    cooldown_base: float = 1.0
    cooldown_max: float = 30.0


@dataclass
class LSPConfig:
    """Configuration for the LSP server."""
    transport: str = "stdio"
    tcp_port: int = 19473
    tcp_host: str = "127.0.0.1"
    predict_on_type: bool = True


@dataclass
class SageConfig:
    """Top-level SAGE configuration."""
    agentic: AgenticConfig = field(default_factory=AgenticConfig)
    lsp: LSPConfig = field(default_factory=LSPConfig)


def _find_config_file() -> Path | None:
    """Find the nearest config file."""
    # Check project-local sage.toml first
    cwd = Path.cwd()
    local = cwd / "sage.toml"
    if local.exists():
        return local

    # Walk up looking for sage.toml
    for parent in cwd.parents:
        candidate = parent / "sage.toml"
        if candidate.exists():
            return candidate

    # Fall back to user config
    sage_dir = Path(os.environ.get("SAGE_DATA_DIR", "")) if os.environ.get("SAGE_DATA_DIR") else Path.home() / ".sage"
    user_config = sage_dir / "config.toml"
    if user_config.exists():
        return user_config

    return None


def load_config() -> SageConfig:
    """Load SAGE configuration from toml file."""
    config_path = _find_config_file()
    if config_path is None:
        return SageConfig()

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return SageConfig()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return SageConfig()

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> SageConfig:
    """Parse raw toml data into config objects."""
    config = SageConfig()

    agentic_data = data.get("agentic", {})
    if agentic_data:
        config.agentic = AgenticConfig(
            autonomy=agentic_data.get("autonomy", config.agentic.autonomy),
            max_retries=agentic_data.get("max_retries", config.agentic.max_retries),
            auto_fix_patterns=agentic_data.get("auto_fix_patterns", config.agentic.auto_fix_patterns),
            never_auto_fix=agentic_data.get("never_auto_fix", config.agentic.never_auto_fix),
            cooldown_base=agentic_data.get("cooldown_base", config.agentic.cooldown_base),
            cooldown_max=agentic_data.get("cooldown_max", config.agentic.cooldown_max),
        )

    lsp_data = data.get("lsp", {})
    if lsp_data:
        config.lsp = LSPConfig(
            transport=lsp_data.get("transport", config.lsp.transport),
            tcp_port=lsp_data.get("tcp_port", config.lsp.tcp_port),
            tcp_host=lsp_data.get("tcp_host", config.lsp.tcp_host),
            predict_on_type=lsp_data.get("predict_on_type", config.lsp.predict_on_type),
        )

    return config
