#!/usr/bin/env python3
"""Water Reach Task - start the graphical interface.

    python run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        import tkinter  # noqa: F401  (availability check)
    except Exception:
        print("ERROR: Tkinter not found. Reinstall Python from python.org "
              "(tick 'tcl/tk and IDLE').")
        sys.exit(1)
    from wrt.gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
