"""fish shell syntax colours, via ~/.config/fish/conf.d/theme-studio.fish.

conf.d files load at startup, so no user file is edited. Global (-g) variables
override fish's universal ones without changing them.
"""
from ..core.color import mix
from ..core.derive import bare
from .base import Action, Target, exists, home, on_path


def fish_theme(p):
    dim = mix(p.on_variant, p.surface, 0.35)
    colours = {
        "fish_color_normal": bare(p.on_surface),
        "fish_color_command": bare(p.primary),
        "fish_color_keyword": bare(p.tertiary),
        "fish_color_quote": bare(p.normal[2]),
        "fish_color_redirection": bare(p.secondary),
        "fish_color_end": bare(p.secondary),
        "fish_color_error": bare(p.error),
        "fish_color_param": bare(p.normal[6]),
        "fish_color_option": bare(p.normal[6]),
        "fish_color_operator": bare(p.normal[3]),
        "fish_color_escape": bare(p.normal[5]),
        "fish_color_comment": bare(dim),
        "fish_color_autosuggestion": bare(dim),
        "fish_color_valid_path": "--underline",
        "fish_color_cwd": bare(p.primary),
        "fish_color_user": bare(p.normal[2]),
        "fish_color_host": bare(p.normal[4]),
        "fish_color_cancel": bare(p.error),
        "fish_color_selection": f"--background={bare(p.hover)}",
        "fish_color_search_match": f"--background={bare(p.variant)}",
        "fish_color_history_current": "--bold",
        "fish_pager_color_prefix": f"{bare(p.primary)} --bold",
        "fish_pager_color_completion": bare(p.on_surface),
        "fish_pager_color_description": bare(p.on_variant),
        "fish_pager_color_progress": f"{bare(p.on_variant)} --background={bare(p.variant)}",
        "fish_pager_color_selected_background": f"--background={bare(p.hover)}",
    }
    lines = [f"# {p.title} ({p.note}) — written by theme-studio. Delete this file to undo."]
    lines += [f"set -g {k} {v}" for k, v in colours.items()]
    return "\n".join(lines) + "\n"


class Fish(Target):
    name = "fish"
    description = "fish shell colours"

    def detect(self):
        return on_path("fish") or exists("~/.config/fish")

    def plan(self, p, cfg, folder):
        return {folder / "theme.fish": fish_theme(p)}

    def apply(self, p, cfg, folder, s):
        dest = home(".config/fish/conf.d/theme-studio.fish")
        return [Action(f"install {dest} (new fish shells use it)",
                       lambda: s.copy_owned(folder / "theme.fish", dest))]
