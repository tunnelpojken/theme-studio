"""Windows: dark or light mode for apps and for Windows itself (taskbar, Start).

HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize
  AppsUseLightTheme     1 = light, 0 = dark
  SystemUsesLightTheme  1 = light, 0 = dark (always 0: Start/taskbar accent needs it)
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
        apps = 0 if p.dark else 1
        # Windows only colours Start and the taskbar with the accent when Windows itself is
        # dark. So a light theme uses Windows' "Custom" mode: light apps, dark Start and
        # taskbar, which can then take the accent colour.
        system = 0
        what = "dark mode" if p.dark else "Custom mode: light apps, Start and taskbar dark so they can take the accent"

        def go():
            s.set_reg(KEY, "AppsUseLightTheme", "REG_DWORD", apps)
            s.set_reg(KEY, "SystemUsesLightTheme", "REG_DWORD", system)
            platform.broadcast_settings_change()
        return [Action(f"set Windows to {what} (registry: Personalize)", go, True)]
