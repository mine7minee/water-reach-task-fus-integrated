# -*- coding: utf-8 -*-
"""
Water Reach Task - visual design (colours, fonts, ttk styles).

All colours and fonts are defined here; edit only this file to change
the look of the interface.
"""
import tkinter as tk
from tkinter import ttk

# =====================================================================
# PALETTE
# =====================================================================
PRIMARY     = "#47b3a1"   # main teal
PRIMARY_DK  = "#2d8273"   # dark teal - headings, accents
PRIMARY_DKR = "#1f6358"   # darkest - pressed button
PRIMARY_LT  = "#e8f5f2"   # light teal background
PRIMARY_LTR = "#f2faf8"   # lightest

INK         = "#14302b"   # heading text
TEXT        = "#2b3f3c"   # body text
MUTED       = "#78908c"   # secondary text
FAINT       = "#9fb2ae"   # very faint

BG          = "#f4f8f7"   # window background
CARD        = "#ffffff"   # card background
BORDER      = "#dbe7e4"   # thin line
BORDER_DK   = "#c3d6d2"

# Status colours
HIT_C       = "#2f9e78"   # green-teal
MISS_C      = "#c25a4f"   # brick red
EARLY_C     = "#d49338"   # amber
FREE_C      = "#5589b5"   # blue
DANGER      = "#b3443a"
WARN        = "#b0792a"

OUTCOME_COLOR = {"touch": HIT_C, "no_touch": MISS_C}

# =====================================================================
# Dark panels
# =====================================================================
D_BG     = "#0e1a18"
D_PANEL  = "#15241f"
D_LINE   = "#243833"
D_TXT    = "#e2efec"
D_MUTED  = "#7b928d"
D_TEAL   = PRIMARY
D_OK     = "#3fb98c"
D_RED    = "#e0695c"
D_AMBER  = "#d9a04a"
D_WATER  = "#4aa8c4"

# =====================================================================
# FONTS
# =====================================================================
def _pick(root, names, size, weight="normal"):
    """Pick the first font that is installed."""
    try:
        from tkinter import font as tkfont
        have = set(tkfont.families(root))
    except Exception:
        have = set()
    for n in names:
        if n in have:
            return (n, size, weight)
    return ("TkDefaultFont", size, weight)


class Fonts:
    def __init__(self, root):
        ui = ["Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans", "Arial"]
        mono = ["Cascadia Mono", "Consolas", "JetBrains Mono",
                "DejaVu Sans Mono", "Courier New"]
        self.h1     = _pick(root, ui, 17, "bold")
        self.h2     = _pick(root, ui, 12, "bold")
        self.h3     = _pick(root, ui, 10, "bold")
        self.body   = _pick(root, ui, 10)
        self.small  = _pick(root, ui, 9)
        self.tiny   = _pick(root, ui, 8)
        self.big    = _pick(root, ui, 13, "bold")
        self.stat   = _pick(root, ui, 20, "bold")
        self.mono   = _pick(root, mono, 10)
        self.tab     = _pick(root, ui, 10, "bold")


# =====================================================================
# ttk STYLES
# =====================================================================
def apply(root):
    """Install all ttk styles. Returns a Fonts object."""
    f = Fonts(root)
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=BG)

    # ---- frames ----
    s.configure("TFrame", background=BG)
    s.configure("Card.TFrame", background=CARD)
    s.configure("Head.TFrame", background=CARD)
    s.configure("Bar.TFrame", background=CARD)
    s.configure("Accent.TFrame", background=PRIMARY_LT)

    # ---- labels ----
    s.configure("TLabel", background=BG, foreground=TEXT, font=f.body)
    s.configure("Card.TLabel", background=CARD, foreground=TEXT, font=f.body)
    s.configure("H1.TLabel", background=CARD, foreground=INK, font=f.h1)
    s.configure("H2.TLabel", background=CARD, foreground=PRIMARY_DK, font=f.h2)
    s.configure("H3.TLabel", background=CARD, foreground=INK, font=f.h3)
    s.configure("Help.TLabel", background=CARD, foreground=MUTED,
                font=f.small, wraplength=640, justify="left")
    s.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=f.small)
    s.configure("StatLbl.TLabel", background=CARD, foreground=MUTED, font=f.tiny)
    s.configure("StatVal.TLabel", background=CARD, foreground=INK, font=f.stat)
    s.configure("Unit.TLabel", background=CARD, foreground=FAINT, font=f.small)
    s.configure("Status.TLabel", background=BG, foreground=MUTED, font=f.small)
    s.configure("Accent.TLabel", background=CARD, foreground=PRIMARY_DK,
                font=f.h3)

    # ---- buttons ----
    # light background + 1px border so buttons are visible on white cards
    s.configure("TButton", font=f.body, padding=(12, 7),
                background=PRIMARY_LTR, foreground=PRIMARY_DK,
                bordercolor=BORDER_DK, lightcolor=PRIMARY_LTR,
                darkcolor=PRIMARY_LTR, borderwidth=1, relief="solid",
                focusthickness=0, anchor="center")
    s.map("TButton",
          background=[("pressed", PRIMARY_LT), ("active", PRIMARY_LT),
                      ("disabled", BG)],
          lightcolor=[("pressed", PRIMARY_LT), ("active", PRIMARY_LT)],
          darkcolor=[("pressed", PRIMARY_LT), ("active", PRIMARY_LT)],
          foreground=[("disabled", FAINT)],
          bordercolor=[("active", PRIMARY), ("focus", PRIMARY)])

    # primary (filled teal) button
    s.configure("Primary.TButton", font=f.big, padding=(20, 12),
                background=PRIMARY, foreground="#ffffff",
                bordercolor=PRIMARY_DK, lightcolor=PRIMARY, darkcolor=PRIMARY,
                borderwidth=1, relief="solid", focusthickness=0)
    s.map("Primary.TButton",
          lightcolor=[("pressed", PRIMARY_DKR), ("active", PRIMARY_DK)],
          darkcolor=[("pressed", PRIMARY_DKR), ("active", PRIMARY_DK)],
          background=[("pressed", PRIMARY_DKR), ("active", PRIMARY_DK),
                      ("disabled", "#dfe9e7")],
          foreground=[("disabled", FAINT)])

    # secondary (outlined) large button
    s.configure("Ghost.TButton", font=f.big, padding=(18, 12),
                background=CARD, foreground=PRIMARY_DK,
                bordercolor=PRIMARY, lightcolor=CARD, darkcolor=CARD,
                borderwidth=1, relief="solid", focusthickness=0)
    s.map("Ghost.TButton",
          lightcolor=[("active", PRIMARY_LTR)], darkcolor=[("active", PRIMARY_LTR)],
          background=[("pressed", PRIMARY_LT), ("active", PRIMARY_LTR),
                      ("disabled", BG)],
          foreground=[("disabled", FAINT)])

    # danger (stop)
    s.configure("Stop.TButton", font=f.big, padding=(18, 12),
                background=CARD, foreground=DANGER,
                bordercolor="#e0bdb8", lightcolor=CARD, darkcolor=CARD,
                borderwidth=1, relief="solid", focusthickness=0)
    s.map("Stop.TButton",
          lightcolor=[("active", "#fbf2f1")], darkcolor=[("active", "#fbf2f1")],
          background=[("pressed", "#f6e6e4"), ("active", "#fbf2f1"),
                      ("disabled", BG)],
          foreground=[("disabled", FAINT)])

    # ---- tabs ----
    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", font=f.tab, padding=(18, 10),
                background=BG, foreground=MUTED, borderwidth=0)
    s.map("TNotebook.Tab",
          background=[("selected", CARD)],
          foreground=[("selected", PRIMARY_DK), ("active", INK)],
          expand=[("selected", (0, 0, 0, 0))])

    # ---- inputs ----
    for st in ("TEntry", "TSpinbox", "TCombobox"):
        s.configure(st, fieldbackground="#ffffff", background="#ffffff",
                    foreground=TEXT, bordercolor=BORDER_DK,
                    arrowcolor=PRIMARY_DK, insertcolor=PRIMARY_DK,
                    padding=5, relief="flat")
        s.map(st,
              bordercolor=[("focus", PRIMARY)],
              fieldbackground=[("readonly", "#ffffff"),
                               ("disabled", BG)],
              foreground=[("disabled", FAINT)])
    s.configure("TCombobox", selectbackground=PRIMARY_LT,
                selectforeground=INK)

    # ---- check / radio buttons ----
    s.configure("TCheckbutton", background=CARD, foreground=TEXT, font=f.body,
                focuscolor=CARD)
    s.map("TCheckbutton", background=[("active", CARD)],
          foreground=[("active", PRIMARY_DK)])
    s.configure("TRadiobutton", background=CARD, foreground=TEXT, font=f.body,
                focuscolor=CARD)
    s.map("TRadiobutton", background=[("active", CARD)],
          foreground=[("active", PRIMARY_DK)])

    # ---- separator / scrollbar ----
    s.configure("TSeparator", background=BORDER)
    s.configure("Vertical.TScrollbar", background=BG, troughcolor=BG,
                bordercolor=BG, arrowcolor=MUTED, relief="flat")
    s.map("Vertical.TScrollbar", background=[("active", PRIMARY_LT)])

    # ---- table ----
    s.configure("Treeview", background=CARD, fieldbackground=CARD,
                foreground=TEXT, font=f.body, rowheight=26,
                bordercolor=BORDER, relief="flat")
    s.configure("Treeview.Heading", background=PRIMARY_LT, foreground=PRIMARY_DK,
                font=f.h3, relief="flat", padding=(6, 7))
    s.map("Treeview.Heading", background=[("active", PRIMARY_LT)])
    s.map("Treeview", background=[("selected", PRIMARY_LT)],
          foreground=[("selected", INK)])

    return f


def card(parent, title=None, fonts=None, pad=16):
    """White card with a thin 1px border and an optional title."""
    outer = tk.Frame(parent, bg=BORDER)          # 1px border
    inner = ttk.Frame(outer, style="Card.TFrame", padding=pad)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    if title:
        head = ttk.Frame(inner, style="Card.TFrame")
        head.pack(fill="x", pady=(0, 12))
        bar = tk.Frame(head, bg=PRIMARY, width=3, height=16)
        bar.pack(side="left", padx=(0, 9))
        bar.pack_propagate(False)
        ttk.Label(head, text=title, style="H2.TLabel").pack(side="left")
    outer.inner = inner
    return outer
