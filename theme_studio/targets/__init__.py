from .fastfetch import Fastfetch
from .fish import Fish
from .hyprland import Hyprland
from .kde import KDE
from .kitty import Kitty
from .konsole import Konsole
from .noctalia import Noctalia
from .wallpaper import Wallpaper
from .waybar import Waybar
from .windows_accent import WindowsAccent
from .windows_mode import WindowsMode
from .windows_terminal import WindowsTerminal
from .windows_theme import WindowsTheme
from .windows_wallpaper import WindowsWallpaper
from ..core.platform import NAME as _PLATFORM

_EVERY = (Hyprland(), Kitty(), Noctalia(), Waybar(), Konsole(), Fish(), Fastfetch(), KDE(), Wallpaper(),
          WindowsMode(), WindowsAccent(), WindowsWallpaper(), WindowsTerminal(), WindowsTheme())
# Only the targets that can exist on this system: Linux ones never show up on Windows and back
ALL = {t.name: t for t in _EVERY if _PLATFORM in t.platforms}


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
