"""waybar: GTK CSS colour variables in ~/.config/waybar/theme-studio.css.

style.css gets one line, `@import "theme-studio.css";`, at the top. The colours
only show where the user's style.css uses them, e.g. `background: @ts_surface;`.
Names are given twice: ts_* and the common base16-style names many configs use.
"""
from ..core.color import on
from ..core.safewrite import css_comment
from .base import Action, Target, exists, home, on_path, signal


def waybar_css(p):
    names = {
        "ts_primary": p.primary, "ts_secondary": p.secondary, "ts_tertiary": p.tertiary,
        "ts_error": p.error, "ts_surface": p.surface, "ts_variant": p.variant, "ts_hover": p.hover,
        "ts_outline": p.outline, "ts_shadow": p.shadow, "ts_on_surface": p.on_surface,
        "ts_on_variant": p.on_variant, "ts_on_primary": on(p.primary),
        # common names
        "background": p.surface, "foreground": p.on_surface, "accent": p.primary,
        "surface0": p.variant, "surface1": p.hover, "overlay0": p.outline, "subtext0": p.on_variant,
        "red": p.normal[1], "green": p.normal[2], "yellow": p.normal[3], "blue": p.normal[4],
        "magenta": p.normal[5], "cyan": p.normal[6], "text": p.on_surface,
    }
    lines = [f"/* {p.title} ({p.note}) — written by theme-studio */"]
    lines += [f"@define-color {k} {v};" for k, v in names.items()]
    return "\n".join(lines) + "\n"


# A full style for people with no style.css of their own. Without one, waybar uses
# the system style, which knows nothing about these colours; and creating a style.css
# with only the import line would drop that style and leave a bare bar.
STARTER = """@import "theme-studio.css";
/* Starter style written by theme-studio, using the theme's colours.
   Delete this file (or use RESTORE ORIGINAL) to go back to waybar's default style.
   Theme Studio counts this file as its own: RESTORE ORIGINAL deletes it, edits included. */

* { font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; font-size: 13px; min-height: 0; }

window#waybar { background: alpha(@ts_surface, 0.94); color: @ts_on_surface;
                border-bottom: 2px solid @ts_outline; }
tooltip { background: @ts_variant; border: 1px solid @ts_outline; border-radius: 6px; }
tooltip label { color: @ts_on_surface; }

#workspaces button { color: @ts_on_variant; background: transparent; padding: 0 8px;
                     border-radius: 0; border-bottom: 2px solid transparent; }
#workspaces button:hover { background: @ts_hover; }
#workspaces button.active, #workspaces button.focused { color: @ts_on_primary; background: @ts_primary; }
#workspaces button.urgent { color: @ts_on_primary; background: @ts_error; }

#clock, #battery, #cpu, #memory, #disk, #temperature, #backlight, #network, #pulseaudio,
#wireplumber, #tray, #idle_inhibitor, #power-profiles-daemon, #keyboard-state, #language,
#mpd, #mode, #custom-power, #custom-media {
    padding: 0 10px; margin: 4px 3px; border-radius: 6px;
    background: @ts_variant; color: @ts_on_surface; }

#clock { color: @ts_primary; }
#cpu, #power-profiles-daemon { color: @ts_secondary; }
#memory, #disk { color: @ts_tertiary; }
#network.disconnected, #pulseaudio.muted, #wireplumber.muted { color: @ts_on_variant; }
#battery.warning, #temperature.critical, #battery.critical:not(.charging) { color: @ts_on_primary; background: @ts_error; }
#custom-power { color: @ts_error; }
"""


class Waybar(Target):
    name = "waybar"
    description = "waybar colour variables"

    def detect(self):
        return on_path("waybar") or exists("~/.config/waybar")

    def plan(self, p, cfg, folder):
        return {folder / "waybar.css": waybar_css(p)}

    def apply(self, p, cfg, folder, s):
        dest, main = home(".config/waybar/theme-studio.css"), home(".config/waybar/style.css")
        line = '@import "theme-studio.css";'
        actions = [Action(f"install {dest}", lambda: s.copy_owned(folder / "waybar.css", dest))]
        empty = main.exists() and not main.read_text(encoding="utf-8").strip()
        if not main.exists() or empty or s.owns(main):
            # No style of their own (or an empty file): a themed starter style that
            # unhook removes again. An empty file is backed up first by write_owned.
            actions.append(Action(f"create {main} (a starter style in the theme's colours; "
                                  f"removed again on restore)", lambda: s.write_owned(main, STARTER)))
        elif not s.has_hook(main, line):
            actions.append(Action(f"add to top of {main}: {line}",
                                  lambda: s.add_hook(main, line, css_comment, where="start"), True))
        def reload():
            # Undo has to reload it too, or waybar keeps showing the last theme's style
            s.remember_cmd("waybar-reload", ["pkill", "-USR2", "-x", "waybar"], "waybar style (reload)")
            signal("waybar", "USR2")
        actions.append(Action("reload waybar", reload))
        return actions
