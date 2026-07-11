"""Entry point for SAGE GUI - run with: python -m sage.gui"""

import sys
from sage.gui.app import SAGEApp


def main():
    """Launch SAGE Desktop GUI"""
    app = SAGEApp()
    app.mainloop()


if __name__ == "__main__":
    sys.exit(main() or 0)
