"""Tidy a model-made palette: small models get the broad idea right but the details
wrong (pure #00ff00 terminal colours, flat grey surfaces, two roles with the same
colour). This keeps every hue the model chose and only fixes lightness/chroma.
Presets are never passed through here.
"""
from dataclasses import replace

from .color import from_oklch, hue_distance, lift_chroma, lift_hue, to_oklch

# Usual OKLCH hues for terminal slots 1-6: red green yellow blue magenta cyan
ANSI_HUES = [25, 145, 95, 255, 330, 200]
HUE_WINDOW = 15

# Lightness ladder for the background roles (dark themes)
LADDER = [("shadow", 0.06, 0.12), ("surface", 0.13, 0.20), ("variant", 0.19, 0.26),
          ("hover", 0.24, 0.31), ("outline", 0.33, 0.42)]


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def tidy(p, tint_ok=True, locked=()):
    """Return (palette, list of change descriptions)."""
    changes = []
    vals = {}

    # 1. Surfaces: a neutral grey stack gets a faint tint of the main accent
    pL, pC, pH = to_oklch(p.primary)
    surf_C = [to_oklch(p[r])[1] for r, *_ in LADDER]
    tint = tint_ok and max(surf_C) < 0.012
    if tint:
        changes.append("tinted the grey backgrounds toward the accent")
    prev = 0.0
    sL, sC0, sH = to_oklch(p.surface)
    tint_hue = sH if sC0 > 0.004 else pH
    for role, lo, hi in LADDER:
        L, C, H = to_oklch(p[role])
        if tint:
            C, H = (0.008 if role == "shadow" else 0.02), tint_hue
        L = _clamp(max(L, prev + 0.035), lo, hi)   # each step visibly lighter than the last
        prev = L
        vals[role] = from_oklch(L, min(C, 0.05), H)

    # 2. Text: on_variant must be softer than on_surface, not a copy of it
    tL, tC, tH = to_oklch(p.on_surface)
    vL, vC, vH = to_oklch(p.on_variant)
    if tL - vL < 0.1:
        vals["on_variant"] = from_oklch(tL - 0.17, max(vC, 0.02), vH if vC > 0.01 else pH)
        changes.append("made dim text softer than main text")

    # 3. Terminal colours: keep each hue, pull pure RGB-cube colours into a calmer range
    def soften(colours, lo, hi, cmax, slot_black, slot_white):
        out, moved = [], 0
        for i, c in enumerate(colours):
            L, C, H = to_oklch(c)
            if i == 0:
                n = vals["variant"] if slot_black else from_oklch(_clamp(L, 0.38, 0.48), min(C, 0.04), H)
            elif i == 7:
                n = from_oklch(_clamp(L, 0.86, 0.97), min(C, 0.03), H)
            else:
                # Each slot stays recognisable: at most ±15° from its usual hue. Green,
                # cyan and blue are only ~55° apart, so a wider window lets them merge.
                base = ANSI_HUES[i - 1]
                d = (H - base + 180) % 360 - 180
                if abs(d) > HUE_WINDOW:
                    H = (base + (HUE_WINDOW if d > 0 else -HUE_WINDOW)) % 360
                C = max(C, 0.09)
                n = from_oklch(_clamp(L, lo, hi), min(C, cmax), H)
            moved += n != c
            out.append(n)
        return out, moved

    normal, m1 = soften(p.normal, 0.66, 0.76, 0.16, True, False)
    bright, m2 = soften(p.bright, 0.76, 0.86, 0.14, False, True)
    if m1 + m2 > 4:
        changes.append("adjusted the terminal colours so each one stays recognisable")

    # 4. Accents too dark to stand out on a dark background: lift them, same hue
    for role in ("primary", "secondary", "tertiary", "error"):
        if role in locked:
            continue
        L, C, H = to_oklch(p[role])
        # Saturated colours may stay deep (crimson, royal blue), like in image mode;
        # only genuinely murky ones are lifted. Contrast is still checked afterwards.
        floor = 0.55 if C > 0.10 else 0.62
        if L < floor:
            L2 = 0.62 if C > 0.10 else (0.66 if role == "error" else 0.70)
            vals[role] = from_oklch(L2, lift_chroma(L, L2, H, max(C, 0.08)), lift_hue(L, L2, H, C))
            changes.append(f"lifted {role} so it stands out ({p[role]} -> {vals[role]})")

    # 5. Two accents that are basically the same colour: shift the second one
    for role in ("secondary", "tertiary"):
        if role in locked:
            continue
        L, C, H = to_oklch(vals.get(role, p[role]))
        if hue_distance(H, pH) < 12 and abs(L - pL) < 0.06 and C > 0.03:
            vals[role] = from_oklch(L, C, (H + 40) % 360)
            changes.append(f"moved {role} away from primary")

    return replace(p, normal=normal, bright=bright, **vals), changes
