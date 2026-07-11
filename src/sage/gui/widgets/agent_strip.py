"""Compact live status cards for the SAGE specialist agents.

Green = active (running/queued/waiting) on the latest run, orange = idle/stopped.
The strip pulls live state from the agents + agent_runs tables so it reflects
the real fan-out that `sage run` performs on every command. The card list is
driven by DEFAULT_AGENT_SPECS, so it always matches the active roster.
"""

from __future__ import annotations

import customtkinter as ctk

from sage.agents import DEFAULT_AGENT_SPECS

# Short glyphs per agent type, reused by the settings panel.
AGENT_ICONS: dict[str, str] = {
    "code": "\U0001f9e9",          # puzzle
    "debug": "\U0001f41b",         # bug
    "test": "\U0001f9ea",          # test tube
    "research": "\U0001f50e",      # magnifier
    "security": "\U0001f512",      # lock
    "performance": "⚡",       # zap
    "docs": "\U0001f4dd",          # memo
    "dependency": "\U0001f4e6",    # package
    "workflow": "\U0001f501",      # loop
    "database": "\U0001f5c4",      # file cabinet
    "frontend": "\U0001f3a8",      # palette
    "release": "\U0001f680",       # rocket
    "architecture": "\U0001f3db",  # classical building
    "review": "\U0001f50d",        # right magnifier
    "refactor": "\U0001f9f9",      # broom
    "devops": "⚙",            # gear
    "api": "\U0001f517",           # link
    "ml": "\U0001f916",            # robot
    "memory": "\U0001f9e0",        # brain
    "telemetry": "\U0001f4e1",     # satellite antenna
    "privacy": "\U0001f6e1",       # shield
    "redteam": "\U0001f6a9",       # triangular flag
    "blueteam": "\U0001f6e1",      # shield
    "auditor": "\U0001f4cb",       # clipboard
}

ACTIVE_COLOR = "#22c55e"   # green
IDLE_COLOR = "#f59e0b"     # orange
_IDLE_BG = ("#E8E8E8", "#242424")
_ACTIVE_BG = ("#dcfce7", "#14351f")


def agent_icon(agent_type: str) -> str:
    return AGENT_ICONS.get(agent_type, "\U0001f9e9")


class AgentCard(ctk.CTkFrame):
    """One tiny agent chip: status dot + short name, with a role tooltip."""

    def __init__(self, master, agent_type: str, name: str, role: str, **kwargs):
        super().__init__(master, corner_radius=6, fg_color=_IDLE_BG, **kwargs)
        self.agent_type = agent_type
        self._role = role
        self.grid_columnconfigure(1, weight=1)

        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=11),
            text_color=IDLE_COLOR,
            width=12,
        )
        self.dot.grid(row=0, column=0, padx=(6, 2), pady=3, sticky="w")

        short = name.replace(" Agent", "").replace(" Team", "").strip()
        self.name_label = ctk.CTkLabel(
            self,
            text=f"{agent_icon(agent_type)} {short}",
            font=ctk.CTkFont(size=10),
            anchor="w",
        )
        self.name_label.grid(row=0, column=1, padx=(0, 6), pady=3, sticky="ew")

    def set_active(self, active: bool) -> None:
        self.dot.configure(text_color=ACTIVE_COLOR if active else IDLE_COLOR)
        self.configure(fg_color=_ACTIVE_BG if active else _IDLE_BG)


class AgentStrip(ctk.CTkFrame):
    """Wrapping grid of specialist agent cards with a live-active count header."""

    COLUMNS = 7

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(tuple(range(self.COLUMNS)), weight=1, uniform="agentcard")

        self._agent_count = len(DEFAULT_AGENT_SPECS)
        self.title = ctk.CTkLabel(
            self,
            text=f"Agents ({self._agent_count}) — 0 active",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray60",
            anchor="w",
        )
        self.title.grid(row=0, column=0, columnspan=self.COLUMNS, padx=2, pady=(0, 3), sticky="w")

        self.cards: dict[str, AgentCard] = {}
        for index, spec in enumerate(DEFAULT_AGENT_SPECS):
            role = spec.description
            card = AgentCard(self, spec.type, spec.name, role, height=24)
            row = 1 + index // self.COLUMNS
            col = index % self.COLUMNS
            card.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            self.cards[spec.type] = card

    def update_active(self, active_types: set[str]) -> None:
        for agent_type, card in self.cards.items():
            card.set_active(agent_type in active_types)
        self.title.configure(text=f"Agents ({self._agent_count}) — {len(active_types)} active")
