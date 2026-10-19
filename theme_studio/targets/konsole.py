"""Konsole (KDE's terminal): a .colorscheme file, set on the default profile."""
import re

from ..core.color import mix
from ..core.derive import triplet
from .base import Action, Target, home, on_path


def colorscheme(p):
    out = []

    def sec(name, colour):
        out.append(f"[{name}]\nColor={triplet(colour)}\n")

    sec("Background", p.surface)
    sec("BackgroundFaint", p.surface)
    sec("BackgroundIntense", p.variant)
    for i in range(8):
        sec(f"Color{i}", p.normal[i])
        sec(f"Color{i}Faint", mix(p.normal[i], p.surface, 0.35))
        sec(f"Color{i}Intense", p.bright[i])
    sec("Foreground", p.on_surface)
    sec("ForegroundFaint", p.on_variant)
    sec("ForegroundIntense", p.bright[7])
    out.append(f"[General]\nBlur=false\nColorRandomization=false\nDescription={p.title}\nOpacity=1\nWallpaper=\n")
    return "\n".join(out)


def set_ini_key(text, section, key, value):
    """Set key=value inside [section] of an INI text, adding either if missing."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == f"[{section}]"), None)
    if start is None:
        return text.rstrip("\n") + ("\n\n" if text.strip() else "") + f"[{section}]\n{key}={value}\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    for i in range(start + 1, end):
        if re.match(rf"^{re.escape(key)}\s*=", lines[i]):
            lines[i] = f"{key}={value}"
            return "\n".join(lines) + "\n"
    lines.insert(start + 1, f"{key}={value}")
    return "\n".join(lines) + "\n"


def default_profile():
    rc = home(".config/konsolerc")
    if rc.exists():
        m = re.search(r"^DefaultProfile=(.+)$", rc.read_text(), re.M)
        if m:
            return m.group(1).strip()
    return None


class Konsole(Target):
    name = "konsole"
    description = "Konsole terminal"

    def detect(self):
        return on_path("konsole")

    def plan(self, p, cfg, folder):
        return {folder / f"{p.palette}.colorscheme": colorscheme(p)}

    def apply(self, p, cfg, folder, s):
        src = folder / f"{p.palette}.colorscheme"
        dest = home(f".local/share/konsole/{p.palette}.colorscheme")
        actions = [Action(f"install {dest}", lambda: s.copy_owned(src, dest))]

        profile_name = default_profile()
        if profile_name:
            # The user's own profile: change one key, after a backup
            prof = home(f".local/share/konsole/{profile_name}")

            def set_scheme():
                s.backup(prof)
                text = prof.read_text() if prof.exists() else ""
                m = re.search(r"^ColorScheme=(.*)$", text, re.M)
                s.remember_ini(prof, "Appearance", "ColorScheme", m.group(1) if m else None)
                prof.write_text(set_ini_key(text, "Appearance", "ColorScheme", p.palette))
            actions.append(Action(f"set ColorScheme={p.palette} in {prof}", set_scheme, True))
        else:
            # No default profile yet: create one the app owns and make it the default
            prof = home(".local/share/konsole/Theme Studio.profile")
            rc = home(".config/konsolerc")
            text = (f"[Appearance]\nColorScheme={p.palette}\n\n[General]\nName=Theme Studio\nParent=FALLBACK/\n")

            def make_default():
                s.write_owned(prof, text)
                s.backup(rc)
                old = rc.read_text() if rc.exists() else ""
                s.remember_ini(rc, "Desktop Entry", "DefaultProfile", None)
                rc.parent.mkdir(parents=True, exist_ok=True)
                rc.write_text(set_ini_key(old, "Desktop Entry", "DefaultProfile", "Theme Studio.profile"))
            actions.append(Action(f"create profile {prof} and make it Konsole's default", make_default, True))
        actions.append(Action("open Konsole windows pick it up on the next new tab/window", lambda: None))
        return actions
