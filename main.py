"""
Handwritten Notes Generator
============================
Entry point – launches the Tkinter GUI.
"""

import tkinter as tk

from app.gui import HandwritingNotesApp


def main() -> None:
    root = tk.Tk()
    app = HandwritingNotesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
