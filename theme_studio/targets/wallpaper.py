"""Wallpaper per monitor on wlroots/Hyprland: awww, swww or hyprpaper.

The first monitor Hyprland lists gets wp1.png, every other one wp2.png.
(KDE sets its own wallpaper in the kde target.)
"""
import json
import re

from .base import Action, Target, on_path, run, session_is


def monitors():
    res = run("hyprctl", "monitors", "-j")
    try:
        return [m["name"] for m in json.loads(res.stdout)] if res else []
    except (ValueError, KeyError, TypeError):
        return []


def tool():
    for name in ("awww", "swww", "hyprpaper"):
        if on_path(name):
            return name
    return None


def current(t):
    """{monitor: image path} showing now, so restore can put them back."""
    out = {}
    if t in ("awww", "swww"):
        res = run(t, "query")
        # e.g. "HDMI-A-1: 2560x1440, scale: 1, currently displaying: image: /path/wp1.png"
        for line in (res.stdout if res else "").splitlines():
            m = re.match(r"^:?\s*([^:\s]+):.*image:\s*(.+?)\s*$", line)
            if m:
                out[m.group(1)] = m.group(2)
    elif t == "hyprpaper":
        res = run("hyprctl", "hyprpaper", "listactive")
        for line in (res.stdout if res else "").splitlines():   # "HDMI-A-1 = /path/wp1.png"
            m = re.match(r"^\s*(\S+)\s*=\s*(.+?)\s*$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def restore_argv(t, mon, img):
    if t == "awww":
        return ["awww", "img", "--outputs", mon, "--transition-type", "fade", img]
    if t == "swww":
        return ["swww", "img", "-o", mon, "--transition-type", "fade", img]
    return ["hyprctl", "hyprpaper", "reload", f"{mon},{img}"]


class Wallpaper(Target):
    name = "wallpaper"
    description = "wallpaper per monitor (awww / swww / hyprpaper)"

    def detect(self):
        return tool() is not None and session_is("Hyprland")

    def apply(self, p, cfg, folder, s):
        wp1, wp2 = folder / "wp1.png", folder / "wp2.png"
        if not wp1.exists():
            return [Action("no wp1.png in the theme, wallpaper left as it is", lambda: None)]
        wp2 = wp2 if wp2.exists() else wp1
        t = tool()

        def go():
            # Note what each monitor shows now (first apply wins), so restore can put it back
            for mon, old in current(t).items():
                s.remember_cmd(f"wallpaper-{mon}", restore_argv(t, mon, old), f"wallpaper on {mon} ({old})")
            mons = monitors()
            for i, mon in enumerate(mons):
                img = str(wp1 if i == 0 else wp2)
                if t == "awww":
                    run("awww", "img", "--outputs", mon, "--transition-type", "fade", img)
                elif t == "swww":
                    run("swww", "img", "-o", mon, "--transition-type", "fade", img)
                elif t == "hyprpaper":
                    run("hyprctl", "hyprpaper", "preload", img)
                    run("hyprctl", "hyprpaper", "wallpaper", f"{mon},{img}")
        return [Action(f"set wallpapers with {t} (first monitor wp1, others wp2)", go)]
