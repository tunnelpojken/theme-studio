"""fastfetch: the distro logo and the info keys in the theme's own colours.

Writes ~/.config/fastfetch/config.jsonc, but only when the user has no fastfetch
config of their own (or it's one theme-studio wrote). A hand-made config is never
replaced: the apply list says so instead. Colours are exact (24-bit), so they look
the same in every terminal, whatever its colour scheme.
"""
import json

from ..core.color import hex_to_rgb
from .base import Action, Target, home, on_path

# fastfetch's own default module list, so the info shown stays the same
MODULES = ["title", "separator", "os", "host", "kernel", "uptime", "packages", "shell",
           "display", "de", "wm", "wmtheme", "theme", "icons", "font", "cursor", "terminal",
           "terminalfont", "cpu", "gpu", "memory", "swap", "disk", "localip", "battery",
           "poweradapter", "locale", "break", "colors"]


def rgb(h):
    r, g, b = hex_to_rgb(h)
    return f"38;2;{r};{g};{b}"


def fastfetch_config(p):
    conf = {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        # logo slots: 1 = main shape, 2 = shading, 3 = small details (e.g. CachyOS's dots)
        "logo": {"color": {"1": rgb(p.primary), "2": rgb(p.secondary), "3": rgb(p.tertiary)}},
        "display": {"color": {"keys": rgb(p.primary), "title": rgb(p.secondary)}},
        "modules": MODULES,
    }
    head = f"// {p.title} — written by theme-studio. Delete this file to undo.\n"
    return head + json.dumps(conf, indent=2) + "\n"


class Fastfetch(Target):
    name = "fastfetch"
    description = "fastfetch logo + key colours"
    platforms = ("linux", "windows")     # fastfetch reads ~/.config/fastfetch on Windows too

    def detect(self):
        return on_path("fastfetch")

    def plan(self, p, cfg, folder):
        return {folder / "fastfetch.jsonc": fastfetch_config(p)}

    def apply(self, p, cfg, folder, s):
        dest = home(".config/fastfetch/config.jsonc")
        if dest.exists() and not s.owns(dest):
            return [Action(f"{dest} is your own config, left as it is "
                           f"(the theme's version is in {folder / 'fastfetch.jsonc'})", lambda: None)]
        return [Action(f"install {dest}", lambda: s.copy_owned(folder / "fastfetch.jsonc", dest))]
