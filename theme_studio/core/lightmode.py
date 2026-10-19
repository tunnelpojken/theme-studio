"""Light themes: turn a finished dark palette into its light counterpart.

Every source (wallpaper rules, directive, preset) builds a dark palette first, so
light mode is one step at the end instead of a second copy of every rule:
  * the background ladder flips: pale surfaces, slightly darker panels, the same
    faint tint the dark version had;
  * text becomes dark, in the background's hue;
  * accents and terminal colours keep their hue and colour but move to a lightness
    that reads on a pale background (vivid but deep, not neon).
The contrast fixer runs afterwards, as for dark themes.
"""
from dataclasses import replace

from .color import from_oklch, to_oklch

# Background ladder for light themes: (role, lightness)
LADDER = [("surface", 0.975), ("variant", 0.935), ("hover", 0.895), ("outline", 0.76), ("shadow", 0.87)]


def _deep(hexcol, lo, hi, cmin=0.0):
    L, C, H = to_oklch(hexcol)
    if 20 <= H <= 75:   # a darkened peach / orange is brown unless it gets more colour (terracotta)
        cmin = max(cmin, 0.12)
    return from_oklch(min(max(L, lo), hi), max(C, cmin), H)


def to_light(p):
    """Return the light version of a dark palette (a light one is returned as it is)."""
    if not p.dark:
        return p
    _, sC, sH = to_oklch(p.surface)
    tinted = sC > 0.004
    tint = min(max(sC, 0.012), 0.03) if tinted else 0.0

    vals = {role: from_oklch(L, tint * (0.6 if role == "outline" else 1.0), sH) for role, L in LADDER}
    vals["on_surface"] = from_oklch(0.24, min(tint * 1.5, 0.03), sH)
    vals["on_variant"] = from_oklch(0.42, min(tint * 1.5, 0.035), sH)

    # Accents: same hue and colour, deep enough to read on a pale background
    vals["primary"] = _deep(p.primary, 0.44, 0.56, 0.08)
    vals["secondary"] = _deep(p.secondary, 0.46, 0.58, 0.06)
    vals["tertiary"] = _deep(p.tertiary, 0.46, 0.60, 0.05)
    eL, eC, eH = to_oklch(p.error)
    vals["error"] = from_oklch(0.55, max(eC, 0.17), eH)

    # Terminal: slot 0 is dark text-grey, slot 7 a light grey; colours 1-6 deepened
    def term(colours, L, black_L, white_L):
        out = []
        for i, c in enumerate(colours):
            cL, cC, cH = to_oklch(c)
            if i == 0:
                out.append(from_oklch(black_L, min(cC, 0.03), sH))
            elif i == 7:
                out.append(from_oklch(white_L, min(cC, 0.02), sH))
            else:
                out.append(from_oklch(L, max(cC, 0.10), cH))
        return out

    return replace(p, dark=False, normal=term(p.normal, 0.54, 0.30, 0.82),
                   bright=term(p.bright, 0.47, 0.45, 0.92), **vals)
