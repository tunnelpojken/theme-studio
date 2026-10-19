"""Extra colour roles some apps need, worked out from the palette."""
from .color import contrast, hex_to_rgb, mix


def triplet(h):
    """'#ff8a3d' -> '255,138,61' (KDE / Konsole format)."""
    return ",".join(str(v) for v in hex_to_rgb(h))


def bare(h):
    """'#ff8a3d' -> 'ff8a3d' (fish format)."""
    return h.lstrip("#")


def text_on(p, bg):
    """Whichever of surface / on_surface reads better on `bg`."""
    return p.surface if contrast(p.surface, bg) >= contrast(p.on_surface, bg) else p.on_surface


def kde_sections(p):
    """{section: {key: '#hex'}} for a KDE .colors file."""
    fg = {
        "ForegroundNormal": p.on_surface,
        "ForegroundInactive": p.on_variant,
        "ForegroundActive": p.primary,
        "ForegroundLink": p.secondary,
        "ForegroundVisited": p.tertiary,
        "ForegroundNegative": p.error,
        "ForegroundNeutral": p.normal[3],
        "ForegroundPositive": p.normal[2],
        "DecorationFocus": p.primary,
        "DecorationHover": p.secondary,
    }

    def group(bg, **over):
        d = {"BackgroundNormal": bg, "BackgroundAlternate": mix(bg, p.on_surface, 0.04), **fg}
        d.update(over)
        return d

    sel_fg = text_on(p, p.primary)
    complementary_bg = mix(p.surface, p.shadow, 0.5)
    return {
        "Colors:Window": group(p.surface),
        "Colors:View": group(p.variant),
        "Colors:Button": group(p.hover),
        "Colors:Header": group(p.surface),
        "Colors:Header][Inactive": group(p.surface),
        "Colors:Tooltip": group(p.variant),
        "Colors:Complementary": group(complementary_bg),
        "Colors:Selection": group(p.primary, BackgroundAlternate=mix(p.primary, p.surface, 0.2),
                                  ForegroundNormal=sel_fg, ForegroundInactive=mix(sel_fg, p.primary, 0.3),
                                  ForegroundActive=sel_fg, ForegroundLink=sel_fg, ForegroundVisited=sel_fg),
    }
