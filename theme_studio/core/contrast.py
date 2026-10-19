"""Readability checks (WCAG contrast ratios) and an automatic fixer.

The fixer only moves lightness in OKLCH, so a fixed colour keeps its hue and
still looks like the colour that was picked.
"""
from dataclasses import replace

from .color import contrast, from_oklch, to_oklch

TEXT_MIN = 7.0     # body text on the background
ACCENT_MIN = 4.5   # secondary text and accents


def checks(p, text_min=TEXT_MIN, accent_min=ACCENT_MIN):
    """(label, foreground role, background role, minimum) for each rule."""
    rules = [
        ("text", "on_surface", "surface", text_min),
        ("text on panels", "on_surface", "variant", accent_min),
        ("dim text", "on_variant", "variant", accent_min),
        ("accent", "primary", "surface", accent_min),
        ("error", "error", "surface", 3.0),
    ]
    return rules


def report(p, **kw):
    """List of (label, fg, bg, ratio, minimum, ok)."""
    rows = []
    for label, fg, bg, minimum in checks(p, **kw):
        ratio = contrast(p[fg], p[bg])
        rows.append((label, fg, bg, ratio, minimum, ratio >= minimum))
    for i, c in enumerate(p.normal[1:7], start=1):
        ratio = contrast(c, p.surface)
        rows.append((f"terminal color{i}", f"normal[{i}]", "surface", ratio, 3.0, ratio >= 3.0))
    return rows


def _push(colour, against, minimum):
    """Move `colour` lighter or darker (away from `against`) until it passes."""
    if contrast(colour, against) >= minimum:
        return colour
    L, C, H = to_oklch(colour)
    bg_L = to_oklch(against)[0]
    step = 0.01 if L >= bg_L or bg_L < 0.5 else -0.01
    for _ in range(100):
        L = max(0.0, min(1.0, L + step))
        colour = from_oklch(L, C, H)
        if contrast(colour, against) >= minimum or L in (0.0, 1.0):
            break
    return colour


def fix(p, **kw):
    """Return a copy of `p` where every check passes, plus a list of changes."""
    changes = []
    current = p
    for label, fg, bg, minimum in checks(p, **kw):
        before = current[fg]
        after = _push(before, current[bg], minimum)
        if after != before:
            changes.append((fg, before, after))
            current = replace(current, **{fg: after})
    normal = list(current.normal)
    for i in range(1, 7):
        after = _push(normal[i], current.surface, 3.0)
        if after != normal[i]:
            changes.append((f"normal[{i}]", normal[i], after))
            normal[i] = after
    return replace(current, normal=normal), changes
