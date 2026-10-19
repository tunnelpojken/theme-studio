"""Where files live and what system this is, so nothing else checks for Windows itself.

Linux keeps the paths it always had. Windows uses its own folders:
  config  %APPDATA%\\theme-studio
  data    %LOCALAPPDATA%\\theme-studio        (themes, undo record, backups)
  cache   %LOCALAPPDATA%\\theme-studio\\cache

Also the small Windows helpers the targets and the undo record share: reading and
writing HKEY_CURRENT_USER values, exporting them as a .reg file, and telling
Windows that its settings changed.
"""
import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
NAME = "windows" if IS_WINDOWS else "linux"


def _env_dir(var, fallback):
    value = os.environ.get(var)
    return Path(value) if value else Path.home() / fallback


def config_dir():
    if IS_WINDOWS:
        return _env_dir("APPDATA", "AppData/Roaming") / "theme-studio"
    return Path.home() / ".config/theme-studio"


def data_dir():
    if IS_WINDOWS:
        return _env_dir("LOCALAPPDATA", "AppData/Local") / "theme-studio"
    return Path.home() / ".local/share/theme-studio"


def cache_dir():
    if IS_WINDOWS:
        return data_dir() / "cache"
    return Path.home() / ".cache/theme-studio"


def default_themes_dir():
    """Existing ~/.config/themes setups (switch.sh style) are used as-is on Linux."""
    if not IS_WINDOWS and (Path.home() / ".config/themes").exists():
        return Path.home() / ".config/themes"
    return data_dir() / "themes"


def local_appdata():
    return _env_dir("LOCALAPPDATA", "AppData/Local")


def utf8_console():
    """Windows consoles default to a legacy code page; the CLI prints · → — and the like."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ---------------------------------------------------------------- registry (Windows only)
# Values are kept as (type, data) with data in a JSON-friendly form:
# REG_DWORD -> int, REG_SZ/REG_EXPAND_SZ -> str, REG_BINARY -> hex string.
REG_TYPES = {"REG_SZ": 1, "REG_EXPAND_SZ": 2, "REG_BINARY": 3, "REG_DWORD": 4}
_NAMES = {v: k for k, v in REG_TYPES.items()}


def reg_get(key, name):
    """('REG_DWORD', 1) etc., or None when the value doesn't exist. key is under HKCU."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            data, kind = winreg.QueryValueEx(k, name)
    except FileNotFoundError:
        return None
    kind_name = _NAMES.get(kind, "REG_BINARY")
    if kind_name == "REG_BINARY":
        data = bytes(data).hex()
    return kind_name, data


def reg_set(key, name, kind, data):
    import winreg
    raw = bytes.fromhex(data) if kind == "REG_BINARY" else data
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, REG_TYPES[kind], raw)


def reg_delete(key, name):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass


def reg_file(entries):
    """A .reg file that restores [(key, name, old)] by double-click, without Theme Studio.
    old = (type, data) or None (the value didn't exist: it is deleted)."""
    lines = ["Windows Registry Editor Version 5.00", ""]
    by_key = {}
    for key, name, old in entries:
        by_key.setdefault(key, []).append((name, old))
    for key, values in by_key.items():
        lines.append(f"[HKEY_CURRENT_USER\\{key}]")
        for name, old in values:
            if old is None:
                lines.append(f'"{name}"=-')
            elif old[0] == "REG_DWORD":
                lines.append(f'"{name}"=dword:{int(old[1]) & 0xFFFFFFFF:08x}')
            elif old[0] == "REG_BINARY":
                h = old[1]
                lines.append(f'"{name}"=hex:' + ",".join(h[i:i + 2] for i in range(0, len(h), 2)))
            else:
                text = str(old[1]).replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'"{name}"="{text}"')
        lines.append("")
    return "\r\n".join(lines) + "\r\n"


def broadcast_settings_change():
    """Tell running apps (Explorer, Start, title bars) that colour settings changed."""
    if not IS_WINDOWS:
        return
    import ctypes
    from ctypes import wintypes
    HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x001A, 0x0002
    result = wintypes.DWORD()
    for area in ("ImmersiveColorSet", "WindowsThemeElement"):
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, area, SMTO_ABORTIFHUNG, 2000, ctypes.byref(result))
