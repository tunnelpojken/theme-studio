"""No-AI role assignment: extracted colours -> a full dark Palette.

Surfaces take the hue of the image's dark tones, accents come from its most
vivid colours, and terminal colours sit at standard hues nudged toward any
matching colour in the image. Lightness is set by rule, so text stays readable.
"""
from ..core.color import from_oklch, hue_distance, lift_chroma, lift_hue, to_oklch
from ..core.palette import Palette, camel

# Standard OKLCH hues for terminal slots 1-6: red green yellow blue magenta cyan
ANSI_HUES = [25, 145, 95, 255, 330, 200]


def _vivid(colours):
    """(score, L, C, H) for colours with real colour in them, best first."""
    out = []
    for hexcol, share in colours:
        L, C, H = to_oklch(hexcol)
        if C > 0.04 and 0.2 < L < 0.97:
            out.append((C * (0.3 + share ** 0.5), L, C, H))
    return sorted(out, reverse=True)


def _pick(vivid, avoid, min_dist=50):
    for item in vivid:
        if all(hue_distance(item[3], h) >= min_dist for h in avoid):
            return item
    return None


def _accent(L, C, H, lo=0.72, hi=0.85):
    # Saturated colours (deep red, royal blue) lose their character when lifted to
    # pastel, so they may sit lower; the contrast fix still guarantees readability.
    if C > 0.10:
        lo = min(lo, 0.60)
    L2 = min(max(L, lo), hi)
    return from_oklch(L2, lift_chroma(L, L2, H, max(C, 0.08)), lift_hue(L, L2, H, C))


def build(colours, name, title=None, note=None, accent=None, bg_hue=None):
    if not colours:
        raise ValueError("no colours to build a theme from")

    # Surface hue: the most common dark tone (fallback: most common colour)
    dark = [(s, *to_oklch(h)) for h, s in colours if to_oklch(h)[0] < 0.45] or \
           [(s, *to_oklch(h)) for h, s in colours]
    _, _, sC, sH = max(dark)
    sC = min(sC * 0.6, 0.035)
    if sC > 0.004:
        sC = max(sC, 0.015)   # a faint tint is the point of a tinted background: keep it visible
    if bg_hue is not None:    # a chosen mood tint (MAGI): same lightness ladder, that hue
        sH, sC = bg_hue, 0.024

    def surf(L, C=sC):
        return from_oklch(L, C, sH)

    vivid = _vivid(colours)
    if accent:  # user's choice wins; it also steers secondary/tertiary away from its hue
        aL, aC, aH = to_oklch(accent)
        vivid = [(9.0, aL, aC, aH)] + [v for v in vivid if hue_distance(v[3], aH) >= 20]
    if vivid:
        _, pL, pC, pH = vivid[0]
    else:  # greyscale image: tinted neutral accent
        pL, pC, pH = 0.8, 0.06, sH
    primary = accent.lower() if accent else _accent(pL, pC, pH)

    sec = _pick(vivid, [pH])
    # No second colour family in the image: an analogous warm/cool step (red -> amber,
    # blue -> violet) reads as intentional, a random complement doesn't
    step = 40 if 0 <= pH < 120 or pH >= 330 else -40
    secondary = _accent(sec[1], sec[2], sec[3], 0.68, 0.80) if sec else from_oklch(0.74, pC * 0.8, (pH + step) % 360)
    sH2 = sec[3] if sec else (pH + step) % 360

    ter = _pick(vivid, [pH, sH2])
    if ter:
        tertiary = _accent(ter[1], ter[2], ter[3], 0.70, 0.85)
    else:
        light = [to_oklch(h) for h, share in colours if to_oklch(h)[0] > 0.62 and share > 0.01]
        if light:   # the image's own light tone, a little warmer/cooler as it is
            lL, lC, lH = max(light, key=lambda x: x[1])
            tertiary = from_oklch(min(max(lL, 0.78), 0.88), min(max(lC, 0.03), 0.07), lH)
        else:
            tertiary = from_oklch(0.80, min(0.09, max(pC * 0.7, 0.04)), (pH + 150) % 360)

    fH = to_oklch(primary)[2]
    error = from_oklch(0.65, 0.18, 33 if hue_distance(fH, 33) > 30 else 18)   # true red; shifts if primary is red

    # Terminal colours: standard hues, pulled toward image colours within 25°
    chroma = sum(v[2] for v in vivid[:6]) / len(vivid[:6]) if vivid else 0.1
    chroma = min(max(chroma, 0.08), 0.15)
    hues = []
    for base in ANSI_HUES:
        near = [v for v in vivid if hue_distance(v[3], base) <= 25]
        hues.append(near[0][3] if near else base)

    normal = [surf(0.24)] + [from_oklch(0.72, chroma, h) for h in hues] + [surf(0.92, 0.02)]
    bright = [surf(0.44, sC)] + [from_oklch(0.81, chroma * 0.9, h) for h in hues] + [surf(0.98, 0.01)]

    title = title or name.replace("-", " ").title()
    return Palette(
        name=name, title=title, palette=camel(name),
        note=note or "Generated from wallpaper colours",
        primary=primary, secondary=secondary, tertiary=tertiary, error=error,
        surface=surf(0.17), variant=surf(0.22), hover=surf(0.27), outline=surf(0.36), shadow=surf(0.08),
        # a neutral (black) background gets neutral text; a tinted one, tinted text
        on_surface=surf(0.93, 0.02 if sC > 0.004 else 0.004), on_variant=surf(0.76, 0.04 if sC > 0.004 else 0.008),
        normal=normal, bright=bright, dark=True,
    )


# ---------------------------------------------------------------- MAGI menu
NAMES = [(27, "red"), (55, "orange"), (72, "amber"), (95, "gold"), (110, "yellow"),
         (135, "lime"), (150, "green"), (175, "sea green"), (195, "teal"), (215, "cyan"),
         (240, "sky blue"), (262, "blue"), (285, "indigo"), (305, "purple"), (330, "magenta"),
         (350, "pink"), (5, "rose")]


def describe(hexcol):
    """Plain words for a colour, so a small model can choose by meaning, not by hex."""
    L, C, H = to_oklch(hexcol)
    if C < 0.025:
        return "silver" if L > 0.75 else "grey" if L > 0.45 else "charcoal"
    if C < 0.06 and L > 0.72:
        return "cream" if 40 <= H <= 110 else "pale " + min(NAMES, key=lambda n: hue_distance(n[0], H))[1]
    if 30 <= H <= 75 and C < 0.13:
        base = "copper" if H < 68 else "bronze" if L < 0.7 else "tan"
    elif 85 <= H <= 125 and C < 0.11:
        base = "olive"
    else:
        base = min(NAMES, key=lambda n: hue_distance(n[0], H))[1]
    tone = "deep " if L < 0.6 else "light " if L > 0.8 else ""
    tone = ("muted " if C < 0.07 else "vivid " if C > 0.17 else "") + tone
    return (tone + base).strip()


def candidates(colours, limit=8):
    """The accent colours a wallpaper offers: the rules palette's three first (so picking
    A, B, C reproduces the no-AI theme exactly), then every other colour family in the
    image, then its light tone. Returns [hex]."""
    base = build(colours, "x")
    out = [base.primary, base.secondary, base.tertiary]
    taken = [to_oklch(c)[2] for c in out if to_oklch(c)[1] > 0.04]
    for _score, L, C, H in _vivid(colours):
        if all(hue_distance(H, t) >= 25 for t in taken):
            out.append(_accent(L, C, H))
            taken.append(H)
        if len(out) >= limit - 1:
            break
    light = [to_oklch(h) for h, share in colours if to_oklch(h)[0] > 0.62 and share > 0.01]
    if light:
        lL, lC, lH = max(light, key=lambda x: (x[1] < 0.06, x[0]))   # the most neutral light tone
        tone = from_oklch(min(max(lL, 0.8), 0.9), min(lC, 0.03), lH)
        if tone not in out:
            out.append(tone)
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:limit]
