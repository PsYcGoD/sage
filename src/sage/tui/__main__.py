"""Allow running SAGE TUI directly: python -m sage.tui"""
from sage.tui.app import SAGETUIApp

if __name__ == "__main__":
    app = SAGETUIApp()
    app.run()
