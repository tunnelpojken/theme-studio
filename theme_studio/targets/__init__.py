from .fastfetch import Fastfetch
from .fish import Fish
from .hyprland import Hyprland
from .kde import KDE
from .kitty import Kitty
from .konsole import Konsole
from .noctalia import Noctalia
from .wallpaper import Wallpaper
from .waybar import Waybar

ALL = {t.name: t for t in (Hyprland(), Kitty(), Noctalia(), Waybar(), Konsole(), Fish(), Fastfetch(), KDE(), Wallpaper())}


def select(setting):
    """Targets from a config value or --targets: "auto", "all" or a list of names."""
    if setting in (None, "auto"):
        return [t for t in ALL.values() if t.detect()]
    if setting == "all":
        return list(ALL.values())
    names = [n.strip() for n in (setting.split(",") if isinstance(setting, str) else setting)]
    unknown = [n for n in names if n not in ALL]
    if unknown:
        raise SystemExit(f"Unknown target(s): {', '.join(unknown)}. Known: {', '.join(ALL)}")
    return [ALL[n] for n in names]
