"""Noctalia V5: a palette JSON plus a noctalia.toml cloned from a template.

palette  -> <noctalia_palettes>/<Palette>.json
config   -> <folder>/noctalia.toml   (switch.sh copies it to config.toml)
"""
import json
import re

from ..core.color import mix, on
from ..core.palette import ANSI as T
from .base import Action, Target, exists, home, on_path, run
from .konsole import set_ini_key


def palette_json(d):
    dark = {
        "mPrimary": d["primary"], "mOnPrimary": on(d["primary"]),
        "mSecondary": d["secondary"], "mOnSecondary": on(d["secondary"]),
        "mTertiary": d["tertiary"], "mOnTertiary": on(d["tertiary"]),
        "mError": d["error"], "mOnError": on(d["error"]),
        "mSurface": d["surface"], "mOnSurface": d["on_surface"],
        "mHover": d["hover"], "mOnHover": d["on_surface"],
        "mSurfaceVariant": d["variant"], "mOnSurfaceVariant": d["on_variant"],
        "mOutline": d["outline"], "mShadow": d["shadow"],
        "terminal": {
            "background": d["surface"], "foreground": d["on_surface"], "cursor": d["primary"],
            "cursorText": d["surface"], "selectionBg": mix(d["surface"], d["primary"], 0.3),
            "selectionFg": d["on_surface"],
            "normal": dict(zip(T, d["normal"])), "bright": dict(zip(T, d["bright"])),
        },
    }
    if not d["dark"]:
        # A light theme is already the light variant; Noctalia gets it for both modes
        return json.dumps({"dark": dark, "light": dark}, indent=2) + "\n"
    # Light variant: pale surface tinted by the accent, darker accents
    lsurf = mix("#f6f6f4", d["primary"], 0.06)
    ltext = mix(d["surface"], "#000000", 0.2)
    light = {
        "mPrimary": mix(d["primary"], "#000000", 0.35), "mOnPrimary": "#ffffff",
        "mSecondary": mix(d["secondary"], "#000000", 0.35), "mOnSecondary": "#ffffff",
        "mTertiary": mix(d["tertiary"], "#000000", 0.35), "mOnTertiary": "#ffffff",
        "mError": mix(d["error"], "#000000", 0.25), "mOnError": "#ffffff",
        "mSurface": lsurf, "mOnSurface": ltext,
        "mHover": mix(lsurf, d["primary"], 0.12), "mOnHover": ltext,
        "mSurfaceVariant": mix(lsurf, d["primary"], 0.08), "mOnSurfaceVariant": mix(ltext, "#ffffff", 0.3),
        "mOutline": mix(d["primary"], "#808080", 0.5), "mShadow": mix(lsurf, "#000000", 0.2),
        "terminal": {
            "background": lsurf, "foreground": ltext, "cursor": mix(d["primary"], "#000000", 0.35),
            "cursorText": lsurf, "selectionBg": mix(lsurf, d["primary"], 0.3), "selectionFg": ltext,
            "normal": dict(zip(T, [lsurf] + [mix(c, "#000000", 0.35) for c in d["normal"][1:7]] + [ltext])),
            "bright": dict(zip(T, [mix(lsurf, "#000000", 0.2)] + [mix(c, "#000000", 0.2) for c in d["bright"][1:7]] + [ltext])),
        },
    }
    return json.dumps({"dark": dark, "light": light}, indent=2) + "\n"


def noctalia_toml(d, template):
    # Template (Rei) colours -> new theme colours
    swaps = {
        "#9fd8e8": d["primary"],                           # accent / capsule border
        "#c9dce8": d["on_surface"],                        # visualizer high
        "#1a2a3a": mix(d["variant"], d["primary"], 0.08),  # capsule fill
        "#0f1c2a": d["variant"],                           # capsule fill (dark)
        "#0a0e14": d["surface"],
        "#0d1b2a": d["variant"],
        "#e8a262": d["error"],
    }
    out = template
    for old, new in swaps.items():
        out = re.sub(re.escape(old), new, out, flags=re.IGNORECASE)
    if not d["dark"]:
        out = re.sub(r'^(mode\s*=\s*)"dark"', r'\1"light"', out, count=1, flags=re.M)
    out = re.sub(r'custom_palette\s*=\s*"[^"]*"', f'custom_palette = "{d["palette"]}"', out)
    # Replace the template's header block with a short one
    out = re.sub(r"\A(#[^\n]*\n)+",
                 f"# {d['title']} — Noctalia V5 Theme\n# {d['note']}\n# Generated from rei-ayanami/noctalia.toml\n",
                 out, count=1)
    return out


def state_mode(path):
    """The raw [theme] mode value in Noctalia's UI state file (e.g. '"light"'), or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    inside = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            inside = s == "[theme]"
        elif inside:
            m = re.match(r'^mode\s*=\s*(.+?)\s*$', s)
            if m:
                return m.group(1)
    return None


class Noctalia(Target):
    name = "noctalia"
    description = "Noctalia V5 shell"

    def detect(self):
        return exists("~/.config/noctalia")

    def plan(self, p, cfg, folder):
        template = cfg.noctalia_template.read_text(encoding="utf-8")
        return {
            cfg.noctalia_palettes / f"{p.palette}.json": palette_json(p),
            folder / "noctalia.toml": noctalia_toml(p, template),
        }

    def apply(self, p, cfg, folder, s):
        # Noctalia V5 merges every *.toml in ~/.config/noctalia alphabetically, so a
        # "zz-" file loads last and only switches the palette. The user's own config
        # (bar layout, widgets) is never touched.
        dest = home(".config/noctalia/zz-theme-studio.toml")
        text = (f"# Written by theme-studio: active palette. Delete this file to undo.\n"
                f"[theme]\nmode = \"{'dark' if p.dark else 'light'}\"\nsource = \"custom\"\ncustom_palette = \"{p.palette}\"\n")
        json_src = cfg.noctalia_palettes / f"{p.palette}.json"
        actions = []
        if not json_src.exists():
            plan = self.plan(p, cfg, folder)
            actions.append(Action(f"install {json_src}", lambda: s.write_owned(json_src, plan[json_src])))
        actions.append(Action(f"install {dest} (palette {p.palette})", lambda: s.write_owned(dest, text)))

        # Noctalia's own UI state loads after every config file and wins. If its
        # [theme] mode disagrees with this theme, change that one line (backed up,
        # put back by unhook); otherwise a dark theme would show its light variant.
        mode = "dark" if p.dark else "light"
        state = home(".local/state/noctalia/settings.toml")
        old = state_mode(state)
        if old is not None and old.strip('"') != mode:
            def set_mode():
                s.backup(state)
                s.remember_ini(state, "theme", "mode", old)
                state.write_text(set_ini_key(state.read_text(encoding="utf-8"), "theme", "mode", f'"{mode}"'))
            actions.append(Action(f"set [theme] mode = \"{mode}\" in {state} (Noctalia's own setting overrides config files)",
                                  set_mode, True))

        # Noctalia doesn't notice a new config file by itself: ask it to reload
        if on_path("noctalia"):
            def reload():
                s.remember_cmd("noctalia-reload", ["noctalia", "msg", "config-reload"], "Noctalia colours (reload)")
                run("noctalia", "msg", "config-reload")
            actions.append(Action("reload Noctalia (noctalia msg config-reload)", reload))
        return actions
