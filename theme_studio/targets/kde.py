"""KDE Plasma: a colour scheme plus the wallpaper.

<folder>/<Palette>.colors -> ~/.local/share/color-schemes/, applied with
plasma-apply-colorscheme; wp1.png applied with plasma-apply-wallpaperimage.
"""
from pathlib import Path

from ..core.derive import kde_sections, triplet
from .base import Action, Target, home, on_path, run, session_is

EFFECTS = """[ColorEffects:Disabled]
Color=56,56,56
ColorAmount=0
ColorEffect=0
ContrastAmount=0.65
ContrastEffect=1
IntensityAmount=0.1
IntensityEffect=2

[ColorEffects:Inactive]
ChangeSelectionColor=true
Color=112,111,110
ColorAmount=0.025
ColorEffect=2
ContrastAmount=0.1
ContrastEffect=2
Enable=false
IntensityAmount=0
IntensityEffect=0
"""


def kde_colors(p):
    out = [EFFECTS]
    for section, keys in kde_sections(p).items():
        body = "\n".join(f"{k}={triplet(v)}" for k, v in sorted(keys.items()))
        out.append(f"[{section}]\n{body}\n")
    out.append(f"[General]\nColorScheme={p.palette}\nName={p.title}\nshadeSortColumn=true\n")
    out.append("[KDE]\ncontrast=4\n")
    wm = {"activeBackground": p.surface, "activeBlend": p.primary, "activeForeground": p.on_surface,
          "inactiveBackground": p.surface, "inactiveBlend": p.outline, "inactiveForeground": p.on_variant}
    out.append("[WM]\n" + "\n".join(f"{k}={triplet(v)}" for k, v in wm.items()) + "\n")
    return "\n".join(out)


def apply_scheme(name):
    res = run("plasma-apply-colorscheme", name)
    # Plasma ignores re-applying the active scheme, even if the file changed:
    # switch away and back so an edited theme takes effect.
    if res and "already" in (res.stdout + res.stderr).lower():
        run("plasma-apply-colorscheme", "BreezeDark")
        run("plasma-apply-colorscheme", name)


def _ini_value(path, section, key):
    """First `key=` value under `[section]` (section may be a prefix like '[Containments]')."""
    try:
        text = path.read_text()
    except OSError:
        return None
    inside = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            inside = s.startswith(section)
        elif inside and s.startswith(key + "="):
            return s[len(key) + 1:]
    return None


def current_scheme():
    """The colour scheme Plasma uses now.

    Plasma 6 keeps ~/.config/kdeglobals sparse: a scheme that comes from the Global
    Theme (Breeze Dark picked in Quick Settings) is only written to
    ~/.config/kdedefaults/kdeglobals. So that file is the next place to look, and
    Plasma's built-in default (Breeze Light) is the last resort."""
    for path in (".config/kdeglobals", ".config/kdedefaults/kdeglobals"):
        scheme = _ini_value(home(path), "[General]", "ColorScheme")
        if scheme:
            return scheme
    return "BreezeLight"


def current_wallpaper():
    """The desktop wallpaper Plasma shows now (an image or a wallpaper package folder)."""
    rc = home(".config/plasma-org.kde.plasma.desktop-appletsrc")
    try:
        text = rc.read_text()
    except OSError:
        return None
    inside = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            inside = s.endswith("[Wallpaper][org.kde.image][General]")
        elif inside and s.startswith("Image="):
            value = s[len("Image="):]
            return value[len("file://"):] if value.startswith("file://") else value
    return None


class KDE(Target):
    name = "kde"
    description = "KDE Plasma colour scheme + wallpaper"

    def detect(self):
        # Only in a Plasma session: on Hyprland, applying a KDE scheme would also restyle Qt apps
        return session_is("KDE") and on_path("plasma-apply-colorscheme")

    def plan(self, p, cfg, folder):
        return {folder / f"{p.palette}.colors": kde_colors(p)}

    def apply(self, p, cfg, folder, s):
        src = folder / f"{p.palette}.colors"
        dest = home(f".local/share/color-schemes/{p.palette}.colors")
        def scheme():
            old = current_scheme()
            mine = home(f".local/share/color-schemes/{old}.colors")
            known = mine.exists() or any(
                (d / f"{old}.colors").exists() for d in map(Path, ("/usr/share/color-schemes", "/usr/local/share/color-schemes")))
            if s.owns(mine) or not known:   # a leftover theme-studio scheme is not the user's own
                old = "BreezeDark"
            if old != p.palette:   # remember the user's own scheme, so unhook can switch back
                s.remember_cmd("kde-scheme", ["plasma-apply-colorscheme", old], f"colour scheme {old}")
            apply_scheme(p.palette)

        actions = [Action(f"install {dest}", lambda: s.copy_owned(src, dest)),
                   Action(f"plasma-apply-colorscheme {p.palette}", scheme)]
        wp = folder / "wp1.png"
        if wp.exists():
            def wallpaper():
                old = current_wallpaper()
                if old and "theme-studio" not in old:   # not one of our own theme wallpapers
                    s.remember_cmd("kde-wallpaper", ["plasma-apply-wallpaperimage", old], f"wallpaper {old}")
                run("plasma-apply-wallpaperimage", str(wp))
            actions.append(Action(f"set Plasma wallpaper to {wp}", wallpaper))
        return actions
