"""ASCII art and terminal styling for the SAGE GUI."""

SAGE_WELCOME = """

    ███████╗ █████╗  ██████╗ ███████╗
    ██╔════╝██╔══██╗██╔════╝ ██╔════╝
    ███████╗███████║██║  ███╗█████╗
    ╚════██║██╔══██║██║   ██║██╔══╝
    ███████║██║  ██║╚██████╔╝███████╗
    ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝

    Smart Agent Guidance Engine V2.0

"""

THINKING_ANIMATION = [
    "- Thinking...",
    "\\ Thinking...",
    "| Thinking...",
    "/ Thinking...",
]

SAGE_PROMPT = "\n[SAGE][{ai}][{mode}]\n> "


def get_welcome_banner(
    ai_name: str = "Claude",
    mode: str = "Full Access",
    tokens_used: int = 0,
    tokens_saved: int = 0,
    compression_ratio: str = "0%",
    run_count: int = 0,
):
    """Get formatted welcome banner with AI info and token stats."""
    banner = SAGE_WELCOME

    if run_count >= 5 and tokens_saved > 0:
        banner += f"    > Token Compression: {compression_ratio}\n"
        banner += f"    > Tokens Used: {tokens_used:,} | Saved: {tokens_saved:,}\n"
    else:
        banner += "    > Multi-AI Support Enabled\n"
        banner += "    > Context Compression Ready\n"

    banner += "\n    =====================================\n"
    banner += f"\n    Connected to: {ai_name} | Mode: {mode}\n"
    return banner
