"""Windows: dark or light mode for apps and for Windows itself (taskbar, Start).

HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize
  AppsUseLightTheme     1 = light, 0 = dark
  SystemUsesLightTheme  1 = light, 0 = dark
Old values go into the undo record first; restore puts them back.
"""
from ..core import platform
from .base import Action, Target

KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


class WindowsMode(Target):
    name = "windows-mode"
    description = "Windows dark / light mode"
    platforms = ("windows",)

    def detect(self):
        return platform.IS_WINDOWS

    def apply(self, p, cfg, folder, s):
        light = 0 if p.dark else 1
        mode = "dark" if p.dark else "light"

        def go():
            s.set_reg(KEY, "AppsUseLightTheme", "REG_DWORD", light)
            s.set_reg(KEY, "SystemUsesLightTheme", "REG_DWORD", light)
            platform.broadcast_settings_change()
        return [Action(f"set Windows and apps to {mode} mode (registry: Personalize)", go, True)]
