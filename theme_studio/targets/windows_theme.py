"""Windows: an entry under Settings -> Personalisation -> Themes.

Writes a .theme file (Windows' own format) to %LOCALAPPDATA%\\Microsoft\\Windows\\Themes.
Picking it in Settings applies the wallpaper, accent and mode without Theme Studio.
Format: https://learn.microsoft.com/windows/win32/controls/themesfileformat-overview
SystemMode / AppMode are what Windows 11 itself writes into saved themes.
"""
from ..core import platform
from .base import Action, Target


def theme_file(p, folder):
    wp = folder / "wp1.png"
    mode = "Dark" if p.dark else "Light"
    rgb = p.primary.lstrip("#").upper()
    lines = [
        "; Written by Theme Studio. Delete this file to remove the entry.",
        "[Theme]",
        f"DisplayName={p.title} (Theme Studio)",
        "",
        r"[Control Panel\Desktop]",
        f"Wallpaper={wp}" if wp.exists() else "Wallpaper=",
        "TileWallpaper=0",
        "WallpaperStyle=10",
        "",
        "[VisualStyles]",
        r"Path=%SystemRoot%\resources\themes\Aero\Aero.msstyles",
        "ColorStyle=NormalColor",
        "Size=NormalSize",
        "AutoColorization=0",
        f"ColorizationColor=0XC4{rgb}",
        f"SystemMode={mode}",
        f"AppMode={mode}",
        "",
        "[MasterThemeSelector]",
        "MTSM=DABJDKT",
        "",
    ]
    return "\r\n".join(lines)


def theme_path(p):
    return platform.local_appdata() / "Microsoft" / "Windows" / "Themes" / f"Theme Studio - {p.title}.theme"


class WindowsTheme(Target):
    name = "windows-theme"
    description = "entry in Settings > Personalisation > Themes"
    platforms = ("windows",)

    def detect(self):
        return platform.IS_WINDOWS

    def plan(self, p, cfg, folder):
        return {folder / "windows.theme": theme_file(p, folder)}

    def apply(self, p, cfg, folder, s):
        dest = theme_path(p)
        # Rewritten at apply time: the wallpaper path must point at the theme's own wp1.png
        return [Action(f"install {dest} (shows under Settings > Personalisation > Themes)",
                       lambda: s.write_owned(dest, theme_file(p, folder)))]
