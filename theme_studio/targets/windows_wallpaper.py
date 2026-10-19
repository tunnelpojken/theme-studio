"""Windows: the wallpaper on each monitor, through IDesktopWallpaper (Windows 8 and later).

The main monitor (the one at position 0,0) gets wp1.png, every other one wp2.png, as on
Hyprland. The image each monitor showed before is remembered so restore can put it back.
The COM interface is called with ctypes, so no extra package is needed.
https://learn.microsoft.com/windows/win32/api/shobjidl_core/nn-shobjidl_core-idesktopwallpaper
"""
from ..core import platform
from .base import Action, Target

CLSID_DesktopWallpaper = "{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}"
IID_IDesktopWallpaper = "{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}"
# Vtable slots after IUnknown's three (QueryInterface, AddRef, Release)
SET_WALLPAPER, GET_WALLPAPER, GET_PATH_AT, GET_PATH_COUNT, GET_RECT = 3, 4, 5, 6, 7
RELEASE = 2


class _Wallpaper:
    """A minimal IDesktopWallpaper client. Use as: with _Wallpaper() as w: ..."""

    def __enter__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.wintypes = ctypes, wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("a", ctypes.c_ulong), ("b", ctypes.c_ushort), ("c", ctypes.c_ushort),
                        ("d", ctypes.c_ubyte * 8)]
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)          # S_FALSE when the thread already has COM: fine
        clsid, iid = GUID(), GUID()
        ole32.CLSIDFromString(CLSID_DesktopWallpaper, ctypes.byref(clsid))
        ole32.CLSIDFromString(IID_IDesktopWallpaper, ctypes.byref(iid))
        self.ptr = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 0x17, ctypes.byref(iid), ctypes.byref(self.ptr))
        if hr != 0 or not self.ptr:
            raise OSError(f"IDesktopWallpaper not available (0x{hr & 0xFFFFFFFF:08x})")
        return self

    def __exit__(self, *exc):
        self._method(RELEASE, restype=self.ctypes.c_ulong)()

    def _method(self, slot, *argtypes, restype=None):
        c = self.ctypes
        vtbl = c.cast(self.ptr, c.POINTER(c.POINTER(c.c_void_p))).contents
        proto = c.WINFUNCTYPE(restype or c.HRESULT, c.c_void_p, *argtypes)
        fn = proto(vtbl[slot])
        return lambda *a: fn(self.ptr, *a)

    def _string(self, raw):
        c = self.ctypes
        text = c.wstring_at(raw) if raw else ""
        if raw:
            c.windll.ole32.CoTaskMemFree(raw)
        return text

    def monitors(self):
        """[(monitor id, is_main)]; the main monitor is the one whose top-left is 0,0."""
        c, w = self.ctypes, self.wintypes
        count = c.c_uint()
        self._method(GET_PATH_COUNT, c.POINTER(c.c_uint))(c.byref(count))
        out = []
        for i in range(count.value):
            raw = c.c_void_p()
            self._method(GET_PATH_AT, c.c_uint, c.POINTER(c.c_void_p))(i, c.byref(raw))
            mon = self._string(raw.value)
            rect = w.RECT()
            try:
                self._method(GET_RECT, c.c_wchar_p, c.POINTER(w.RECT))(mon, c.byref(rect))
                main = rect.left == 0 and rect.top == 0
            except OSError:        # a monitor that's listed but not attached
                continue
            out.append((mon, main))
        return out

    def get(self, mon):
        c = self.ctypes
        raw = c.c_void_p()
        self._method(GET_WALLPAPER, c.c_wchar_p, c.POINTER(c.c_void_p))(mon, c.byref(raw))
        return self._string(raw.value)

    def set(self, mon, path):
        c = self.ctypes
        self._method(SET_WALLPAPER, c.c_wchar_p, c.c_wchar_p)(mon, path)


def restore(mon, path):
    """Undo: put back the image a monitor showed before Theme Studio."""
    with _Wallpaper() as w:
        w.set(mon, path)


class WindowsWallpaper(Target):
    name = "windows-wallpaper"
    description = "wallpaper per monitor (Windows)"
    platforms = ("windows",)

    def detect(self):
        return platform.IS_WINDOWS

    def apply(self, p, cfg, folder, s):
        wp1, wp2 = folder / "wp1.png", folder / "wp2.png"
        if not wp1.exists():
            return [Action("no wp1.png in the theme, wallpaper left as it is", lambda: None)]
        wp2 = wp2 if wp2.exists() else wp1

        def go():
            with _Wallpaper() as w:
                mons = sorted(w.monitors(), key=lambda m: not m[1])   # main monitor first
                for i, (mon, main) in enumerate(mons):
                    old = w.get(mon)
                    if old and "theme-studio" not in old.lower():   # not one of our own theme images
                        s.remember_call(f"wallpaper-{mon}", "theme_studio.targets.windows_wallpaper:restore",
                                        [mon, old], f"wallpaper on monitor {i + 1} ({old})")
                    w.set(mon, str(wp1 if i == 0 else wp2))
        return [Action("set the wallpaper on each monitor (main monitor wp1, others wp2)", go)]
