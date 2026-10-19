"""Colour maths: hex helpers, WCAG contrast and OKLCH conversion.

`mix` and `on` are copied unchanged from make-themes.py so existing themes
regenerate byte for byte.
"""
import math


def mix(a, b, t):
    """Blend hex colour a towards b by t (0..1)."""
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def on(color):
    """Readable text colour on top of `color`."""
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return "#0a0a0a" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#f4f4f4"


# ---------------------------------------------------------------- hex / rgb

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c):
    c = max(0.0, min(1.0, c))
    return 255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


# ---------------------------------------------------------------- WCAG

def luminance(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- OKLCH

def to_oklch(h):
    r, g, b = (_lin(v) for v in hex_to_rgb(h))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def _oklch_to_lin(L, C, H):
    A, B = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def from_oklch(L, C, H):
    """OKLCH -> hex. Chroma is reduced until the colour fits in sRGB, so hue holds."""
    L = max(0.0, min(1.0, L))
    for _ in range(40):
        rgb = _oklch_to_lin(L, C, H)
        if all(-0.0005 <= v <= 1.0005 for v in rgb):
            break
        C *= 0.92
    return rgb_to_hex(_delin(v) for v in _oklch_to_lin(L, C, H))


def _is_brown(L_from, L_to, H, C):
    # Browns are dark, muted oranges. Crimson / scarlet (high chroma) are not browns.
    return (20 <= H <= 62 and C < 0.13 or 5 <= H < 20 and C < 0.08) and L_to - L_from > 0.12


def lift_hue(L_from, L_to, H, C=0.0):
    """Hue to use when a colour is made lighter. Browns (dark oranges, hue ~20-60)
    turn salmon-pink if lifted at the same hue; real light leather/wood reads as
    copper or amber, so the hue moves toward ~68 in proportion to the lift."""
    if _is_brown(L_from, L_to, H, C):
        pull = min(1.0, (L_to - L_from) / 0.25)
        return H + (68 - H) * 0.85 * pull
    return H


def lift_chroma(L_from, L_to, H, C):
    """Lifted browns need more colour too, or they read as beige/peach."""
    if _is_brown(L_from, L_to, H, C):
        return max(C, 0.11)
    return C


def hue_distance(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)
