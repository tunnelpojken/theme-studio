"""kitty terminal colours: <folder>/kitty.conf."""
from ..core.color import mix, on
from ..core.safewrite import hash_comment
from .base import Action, Target, exists, home, on_path, signal


def kitty_conf(d):
    lines = [
        f"# {d['title']} — {d['note']}",
        f"background            {d['surface']}",
        f"foreground            {d['on_surface']}",
        f"cursor                {d['primary']}",
        f"cursor_text_color     {d['surface']}",
        f"selection_background  {mix(d['surface'], d['primary'], 0.3)}",
        f"selection_foreground  {d['on_surface']}",
        f"url_color             {d['secondary']}",
        f"active_border_color   {d['primary']}",
        f"inactive_border_color {d['outline']}",
        f"active_tab_background   {d['primary']}",
        f"active_tab_foreground   {on(d['primary'])}",
        f"inactive_tab_background {d['variant']}",
        f"inactive_tab_foreground {d['on_variant']}",
        "",
    ]
    for i, c in enumerate(d["normal"] + d["bright"]):
        lines.append(f"color{i:<2}  {c}")
    return "\n".join(lines) + "\n"


class Kitty(Target):
    name = "kitty"
    description = "kitty terminal"

    def detect(self):
        return on_path("kitty") or exists("~/.config/kitty")

    def plan(self, p, cfg, folder):
        return {folder / "kitty.conf": kitty_conf(p)}

    def apply(self, p, cfg, folder, s):
        dest, main = home(".config/kitty/theme-studio.conf"), home(".config/kitty/kitty.conf")
        line = "include theme-studio.conf"
        actions = [Action(f"install {dest}", lambda: s.copy_owned(folder / "kitty.conf", dest))]
        if not s.has_hook(main, line):
            actions.append(Action(f"add to {main}: {line}", lambda: s.add_hook(main, line, hash_comment), True))
        actions.append(Action("reload open kitty windows", lambda: signal("kitty", "USR1")))
        return actions
