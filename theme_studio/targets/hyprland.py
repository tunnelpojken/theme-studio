"""Hyprland window border colours.

Writes both formats into the theme folder:
  <name>.lua      Lua config (Hyprland 0.55+), same format as the hand-made themes
  hyprland.conf   classic hyprlang config
`apply` installs whichever one this machine uses.
"""
from ..core.safewrite import hash_comment, lua_comment
from .base import Action, Target, exists, home, on_path, run


def hypr_lua(d):
    """Hyprland 0.55+ Lua: border colours through hl.config. (The older
    `hl.general = {...}` form from make-themes.py sets nothing in 0.55.)"""
    a, b = d["primary"][1:], d["secondary"][1:]
    inactive = d["outline"][1:]
    return (
        f"-- {d['title']} Theme ({d['note']})\n"
        "hl.config({\n"
        "    general = {\n"
        "        col = {\n"
        f'            active_border = {{ colors = {{ "rgba({a}ff)", "rgba({b}ff)" }}, angle = 45 }},\n'
        f'            inactive_border = "rgba({inactive}aa)",\n'
        "        },\n"
        "    },\n"
        "})\n"
    )


def hypr_conf(d):
    a, b = d["primary"][1:], d["secondary"][1:]
    return (
        f"# {d['title']} ({d['note']})\n"
        "general {\n"
        f"    col.active_border = rgba({a}ff) rgba({b}ff) 45deg\n"
        f"    col.inactive_border = rgba({d['outline'][1:]}aa)\n"
        "}\n"
    )


class Hyprland(Target):
    name = "hyprland"
    description = "Hyprland window borders"

    def detect(self):
        return on_path("hyprctl") or exists("~/.config/hypr")

    def plan(self, p, cfg, folder):
        return {folder / f"{p.name}.lua": hypr_lua(p), folder / "hyprland.conf": hypr_conf(p)}

    def apply(self, p, cfg, folder, s):
        lua_main = home(".config/hypr/hyprland.lua")
        if lua_main.exists():
            src, dest = folder / f"{p.name}.lua", home(".config/hypr/theme-studio.lua")
            main, line, comment = lua_main, cfg.hypr_lua_include, lua_comment
        else:
            src, dest = folder / "hyprland.conf", home(".config/hypr/theme-studio.conf")
            main, line, comment = home(".config/hypr/hyprland.conf"), "source = ~/.config/hypr/theme-studio.conf", hash_comment
        actions = [Action(f"install {dest}", lambda: s.copy_owned(src, dest))]
        if not s.has_hook(main, line):
            actions.append(Action(f"add to {main}: {line}", lambda: s.add_hook(main, line, comment), True))
        def reload():
            # Undo ends with a reload too, so Hyprland reads the config without our include
            s.remember_cmd("hyprland-reload", ["hyprctl", "reload"], "Hyprland colours (reload)")
            run("hyprctl", "reload")
        actions.append(Action("reload Hyprland", reload))
        return actions
