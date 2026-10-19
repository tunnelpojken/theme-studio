"""Windows: the accent colour (Start, taskbar, title bars, focus outlines).

Windows keeps the accent in three places under HKCU\\Software\\Microsoft\\Windows:
  CurrentVersion\\Explorer\\Accent  AccentPalette   REG_BINARY, 8 colours x (R, G, B, 0):
                                                    3 lighter shades, the accent, 3 darker,
                                                    then a complementary colour
                                    AccentColorMenu REG_DWORD 0xAABBGGRR, the accent
                                    StartColorMenu  REG_DWORD, a darker shade (Start, taskbar)
  DWM                               AccentColor     0xAABBGGRR, ColorizationColor 0xAARRGGBB,
                                    ColorPrevalence 1 = accent on title bars and borders
  CurrentVersion\\Themes\\Personalize ColorPrevalence 1 = accent on Start and taskbar (dark only)
AccentPalette's layout isn't documented by Microsoft; it follows what Windows writes itself.
Every old value goes into the undo record first.
"""
from ..core import platform
from ..core.color import from_oklch, hex_to_rgb, to_oklch
from .base import Action, Target

ACCENT = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
DWM = r"Software\Microsoft\Windows\DWM"
PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

# Lightness steps around the accent, as in Windows' own palettes (lightest first)
STEPS = [0.30, 0.19, 0.09, 0.0, -0.06, -0.16, -0.27]


def palette(hexcol):
    """The 8 colours of AccentPalette, as hex."""
    L, C, H = to_oklch(hexcol)
    out = [hexcol if d == 0 else from_oklch(min(max(L + d, 0.12), 0.95), C, H) for d in STEPS]
    out.append(from_oklch(0.68, max(C, 0.12), (H + 180) % 360))   # the complementary colour
    return out


def palette_bytes(hexcol):
    return "".join(f"{r:02x}{g:02x}{b:02x}00" for r, g, b in map(hex_to_rgb, palette(hexcol)))


def abgr(hexcol, alpha=0xFF):
    r, g, b = hex_to_rgb(hexcol)
    return (alpha << 24) | (b << 16) | (g << 8) | r


def argb(hexcol, alpha=0xC4):
    r, g, b = hex_to_rgb(hexcol)
    return (alpha << 24) | (r << 16) | (g << 8) | b


class WindowsAccent(Target):
    name = "windows-accent"
    description = "Windows accent colour (Start, taskbar, title bars)"
    platforms = ("windows",)

    def detect(self):
        return platform.IS_WINDOWS

    def apply(self, p, cfg, folder, s):
        accent = p.primary
        shades = palette(accent)

        def go():
            s.set_reg(ACCENT, "AccentPalette", "REG_BINARY", palette_bytes(accent))
            s.set_reg(ACCENT, "AccentColorMenu", "REG_DWORD", abgr(accent))
            s.set_reg(ACCENT, "StartColorMenu", "REG_DWORD", abgr(shades[4]))
            s.set_reg(DWM, "AccentColor", "REG_DWORD", abgr(accent))
            s.set_reg(DWM, "ColorizationColor", "REG_DWORD", argb(accent))
            s.set_reg(DWM, "ColorizationAfterglow", "REG_DWORD", argb(accent))
            s.set_reg(DWM, "ColorPrevalence", "REG_DWORD", 1)
            # Windows only shows the accent on Start and the taskbar in dark mode
            s.set_reg(PERSONALIZE, "ColorPrevalence", "REG_DWORD", 1 if p.dark else 0)
            platform.broadcast_settings_change()
        where = "Start, taskbar and title bars" if p.dark else "title bars (light mode keeps Start and taskbar light)"
        return [Action(f"set the accent colour to {accent} on {where} (registry: Accent, DWM)", go, True)]
