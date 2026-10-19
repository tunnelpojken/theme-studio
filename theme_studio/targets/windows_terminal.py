"""Windows Terminal: the theme as a colour scheme, made the default for every profile.

1. The scheme lives in a fragment Theme Studio owns:
   %LOCALAPPDATA%\\Microsoft\\Windows Terminal\\Fragments\\theme-studio\\theme-studio.json
   https://learn.microsoft.com/windows/terminal/json-fragment-extensions
2. One key in the user's settings.json selects it: profiles.defaults.colorScheme.
   settings.json allows comments and trailing commas, so it is edited as text around that
   key, never re-saved through a JSON library; everything else in it stays byte for byte.
   Backed up first; restore puts the old value back (or removes the key if there was none).
Terminal reloads settings.json by itself.
"""
import json
from pathlib import Path

from ..core import platform
from .base import Action, Target, on_path

PACKAGES = ["Microsoft.WindowsTerminal_8wekyb3d8bbwe", "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe"]


def settings_files():
    """settings.json for each Windows Terminal that is installed (Store, Preview, unpackaged)."""
    base = platform.local_appdata()
    found = [base / "Packages" / pkg / "LocalState" / "settings.json" for pkg in PACKAGES]
    found.append(base / "Microsoft" / "Windows Terminal" / "settings.json")
    return [f for f in found if f.exists()]


def fragment_path():
    return platform.local_appdata() / "Microsoft" / "Windows Terminal" / "Fragments" / "theme-studio" / "theme-studio.json"


def scheme_name(p):
    return f"Theme Studio - {p.title}"


def scheme(p):
    names = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white"]
    s = {"name": scheme_name(p), "background": p.surface, "foreground": p.on_surface,
         "cursorColor": p.primary, "selectionBackground": p.hover}
    for i, n in enumerate(names):
        s[n] = p.normal[i]
        s["bright" + n[0].upper() + n[1:]] = p.bright[i]
    return {"schemes": [s]}


# ---------------------------------------------------------------- JSON-with-comments editing
def members(text):
    """[(path, key, key_start, value_start, value_end)] for every object member in `text`.
    Tolerates // and /* */ comments and trailing commas, as Terminal does."""
    out, n = [], len(text)

    def ws(i):
        while i < n:
            if text[i] in " \t\r\n":
                i += 1
            elif text.startswith("//", i):
                j = text.find("\n", i)
                i = n if j < 0 else j + 1
            elif text.startswith("/*", i):
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
            else:
                break
        return i

    def string(i):          # text[i] == '"'; returns index after the closing quote
        i += 1
        while i < n and text[i] != '"':
            i += 2 if text[i] == "\\" else 1
        return i + 1

    def value(i, path):
        i = ws(i)
        if i >= n:
            return i
        c = text[i]
        if c == "{":
            i += 1
            while True:
                i = ws(i)
                if i >= n or text[i] == "}":
                    return i + 1
                if text[i] == ",":
                    i += 1
                    continue
                key_start = i
                i = string(i)
                key = json.loads(text[key_start:i])
                i = ws(i) + 1                  # the ':'
                vs = ws(i)
                ve = value(vs, path + [key])
                out.append((tuple(path), key, key_start, vs, ve))
                i = ve
        if c == "[":
            i += 1
            while True:
                i = ws(i)
                if i >= n or text[i] == "]":
                    return i + 1
                if text[i] == ",":
                    i += 1
                    continue
                i = value(i, path + ["[]"])
        if c == '"':
            return string(i)
        while i < n and text[i] not in ",}] \t\r\n/":
            i += 1
        return i

    value(0, [])
    return out


def _find(text, path, key):
    for p, k, ks, vs, ve in members(text):
        if p == tuple(path) and k == key:
            return ks, vs, ve
    return None


def get_default_scheme(text):
    m = _find(text, ["profiles", "defaults"], "colorScheme")
    return json.loads(text[m[1]:m[2]]) if m else None


def _remove(text, ks, ve):
    """Delete the member text[ks:ve] and its comma, and the line it leaves empty."""
    j = ve
    while j < len(text) and text[j] in " \t\r\n":
        j += 1
    if j < len(text) and text[j] == ",":          # a member follows: take our trailing comma
        start, end = ks, j + 1
    else:                                         # the last member: take the comma before it
        i = ks - 1
        while i >= 0 and text[i] in " \t\r\n":
            i -= 1
        start, end = (i, ve) if i >= 0 and text[i] == "," else (ks, ve)
    line_start = text.rfind("\n", 0, start) + 1
    if not text[line_start:start].strip():
        line_end = text.find("\n", end)
        if line_end != -1 and not text[end:line_end].strip():
            start, end = line_start, line_end + 1
    return text[:start] + text[end:]


def set_default_scheme(text, name):
    """Return text with profiles.defaults.colorScheme = name (None removes the key)."""
    m = _find(text, ["profiles", "defaults"], "colorScheme")
    if name is None:
        return _remove(text, m[0], m[2]) if m else text
    value = json.dumps(name)
    if m:
        return text[:m[1]] + value + text[m[2]:]
    d = _find(text, ["profiles"], "defaults")
    if d:
        _ks, vs, ve = d
        inner = text[vs + 1:ve - 1]
        if not inner.strip():
            return text[:vs] + "{\n            \"colorScheme\": " + value + "\n        }" + text[ve:]
        return text[:vs + 1] + "\n            \"colorScheme\": " + value + "," + text[vs + 1:]
    prof = _find(text, [], "profiles")
    if prof and text[prof[1]] == "{":
        vs = prof[1]
        return text[:vs + 1] + "\n        \"defaults\": { \"colorScheme\": " + value + " }," + text[vs + 1:]
    raise ValueError("settings.json has no profiles object to put a default colour scheme in")


def defaults_text(text):
    """The profiles.defaults value exactly as written, or None if there is none."""
    d = _find(text, ["profiles"], "defaults")
    return text[d[1]:d[2]] if d else None


def restore(path, old, old_defaults="__unknown__"):
    """Undo: put the user's own default colour scheme back, as it was written.
    If Theme Studio made the defaults object itself, it is put back as it was (or removed)."""
    f = Path(path)
    if not f.exists():
        return
    import re
    text = f.read_text(encoding="utf-8")
    only_ours = [m[1] for m in members(text) if m[0] == ("profiles", "defaults")] == ["colorScheme"]
    d = _find(text, ["profiles"], "defaults")
    if old is None and old_defaults != "__unknown__" and d:
        if old_defaults is None and only_ours:         # Theme Studio made "defaults": remove it
            text = _remove(text, d[0], d[2])
        else:
            without = set_default_scheme(text, None)
            d2 = _find(without, ["profiles"], "defaults")
            same = old_defaults is not None and d2 and \
                re.sub(r"\s", "", without[d2[1]:d2[2]]) == re.sub(r"\s", "", old_defaults)
            # Nothing else changed in defaults since: put back exactly what the user had
            text = without[:d2[1]] + old_defaults + without[d2[2]:] if same else without
    else:
        text = set_default_scheme(text, old)
    f.write_text(text, encoding="utf-8")


class WindowsTerminal(Target):
    name = "windows-terminal"
    description = "Windows Terminal colour scheme"
    platforms = ("windows",)

    def detect(self):
        return platform.IS_WINDOWS and (bool(settings_files()) or on_path("wt"))

    def plan(self, p, cfg, folder):
        return {folder / "windows-terminal.json": json.dumps(scheme(p), indent=2) + "\n"}

    def apply(self, p, cfg, folder, s):
        frag = fragment_path()
        actions = [Action(f"install {frag} (scheme '{scheme_name(p)}')",
                          lambda: s.write_owned(frag, json.dumps(scheme(p), indent=2) + "\n"))]
        files = settings_files()
        if not files:
            actions.append(Action("Windows Terminal has no settings.json yet: open it once, then apply again",
                                  lambda: None))
        for f in files:
            def go(f=f):
                text = f.read_text(encoding="utf-8")
                s.backup(f)
                s.remember_call(f"terminal-{f}", "theme_studio.targets.windows_terminal:restore",
                                [str(f), get_default_scheme(text), defaults_text(text)],
                                f"Windows Terminal colour scheme in {f.name}")
                f.write_text(set_default_scheme(text, scheme_name(p)), encoding="utf-8")
            actions.append(Action(f"set the default colour scheme in {f}", go, True))
        actions.append(Action("open Terminal tabs switch on their own (Terminal reloads its settings)", lambda: None))
        return actions
