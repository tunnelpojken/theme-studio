"""Changing files outside the theme folder, safely.

Rules:
  * the app only fully owns files it created (recorded in owned.json);
  * a user's own config only ever gets ONE marked include line, added after asking;
  * any user file is backed up before its first change in a run;
  * `theme-studio unhook` removes every include line again.
"""
import json
import shutil
import time
from pathlib import Path

MARK = "theme-studio"


class Session:
    """One apply/make run: shared backup folder and the record of owned files and hooks."""

    def __init__(self, data_dir):
        self.data = Path(data_dir)
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.backed_up = set()
        self.state_file = self.data / "state.json"
        try:
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = {}
        self.state.setdefault("owned", [])
        self.state.setdefault("hooks", [])
        self.state.setdefault("ini", [])     # [{file, section, key, old}] values changed in user files
        self.state.setdefault("restore", [])  # [{key, argv, what}] commands that put live settings back
        self.state.setdefault("reg", [])      # [{key, name, old}] Windows registry values (HKCU) changed

    def save(self):
        self.data.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ backups
    def backup(self, path):
        path = Path(path)
        if not path.exists() or path in self.backed_up:
            return None
        try:
            rel = path.resolve().relative_to(Path.home())
        except ValueError:
            rel = Path(str(path.resolve()).lstrip("/"))
        dest = self.data / "backups" / self.stamp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        self.backed_up.add(path)
        return dest

    # ------------------------------------------------------------ owned files
    def owns(self, path):
        return str(Path(path)) in self.state["owned"]

    def write_owned(self, path, text):
        """Write a file the app owns. A same-named file the user made is backed up first."""
        path = Path(path)
        if path.exists() and not self.owns(path):
            self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if str(path) not in self.state["owned"]:
            self.state["owned"].append(str(path))

    def copy_owned(self, src, path):
        path = Path(path)
        if path.exists() and not self.owns(path):
            self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, path)
        if str(path) not in self.state["owned"]:
            self.state["owned"].append(str(path))

    # ------------------------------------------------------------ include lines
    @staticmethod
    def marked(line, comment):
        return f"{line}  {comment(MARK)}"

    def has_hook(self, path, line):
        path = Path(path)
        return path.exists() and any(l.strip().startswith(line) for l in path.read_text(encoding="utf-8").splitlines())

    def add_hook(self, path, line, comment, where="end"):
        """Add `line` (with a marker comment) to a user config. Creates the file if missing."""
        path = Path(path)
        if self.has_hook(path, line):
            return False
        created = not path.exists()
        self.backup(path)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        new = self.marked(line, comment)
        if where == "start":
            text = new + "\n" + text
        else:
            text = text + ("" if text.endswith("\n") or not text else "\n") + new + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.state["hooks"].append({"file": str(path), "line": line, "created": created})
        return True

    def remember_ini(self, path, section, key, old):
        """Record a user setting before the app changes it (first change wins)."""
        if not any(e["file"] == str(path) and e["key"] == key for e in self.state["ini"]):
            self.state["ini"].append({"file": str(path), "section": section, "key": key, "old": old})

    def remember_reg(self, key, name):
        """Record a HKCU registry value before the app changes it (first change wins).
        Also writes a .reg file to the backups folder that restores it by double-click."""
        from . import platform
        if any(e["key"] == key and e["name"] == name for e in self.state["reg"]):
            return
        old = platform.reg_get(key, name)
        self.state["reg"].append({"key": key, "name": name, "old": list(old) if old else None})
        dest = self.data / "backups" / "registry-before-theme-studio.reg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        entries = [(e["key"], e["name"], e["old"]) for e in self.state["reg"]]
        dest.write_text(platform.reg_file(entries), encoding="utf-8-sig")   # regedit wants a BOM

    def set_reg(self, key, name, kind, data):
        """Change a HKCU value, remembering the old one first."""
        from . import platform
        self.remember_reg(key, name)
        platform.reg_set(key, name, kind, data)

    def remember_cmd(self, key, argv, what):
        """Record how to put a live setting back (a desktop's colour scheme, its wallpaper).
        First apply wins, so unhook returns to what the user had before theme-studio."""
        if argv and not any(e["key"] == key for e in self.state["restore"]):
            self.state["restore"].append({"key": key, "argv": list(argv), "what": what})

    def unhook(self, set_ini_key=None, run_restore=True):
        """Remove every marked line the app added and restore changed settings. Returns the files changed.
        With run_restore=False the live-setting commands are left for run_restore()."""
        changed = []
        for e in list(self.state["ini"]):
            path = Path(e["file"])
            if path.exists() and set_ini_key:
                self.backup(path)
                text = path.read_text(encoding="utf-8")
                if e["old"] is None:   # key didn't exist before: remove it
                    text = "".join(l for l in text.splitlines(keepends=True)
                                   if not l.startswith(e["key"] + "="))
                else:
                    text = set_ini_key(text, e["section"], e["key"], e["old"])
                path.write_text(text, encoding="utf-8")
                changed.append(path)
            self.state["ini"].remove(e)
        if self.state["reg"]:
            from . import platform
            for e in list(self.state["reg"]):
                if e["old"] is None:
                    platform.reg_delete(e["key"], e["name"])
                else:
                    platform.reg_set(e["key"], e["name"], e["old"][0], e["old"][1])
                self.state["reg"].remove(e)
            self._broadcast = True
        for hook in list(self.state["hooks"]):
            path = Path(hook["file"])
            if path.exists():
                lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
                kept = [l for l in lines if not (l.strip().startswith(hook["line"]) and MARK in l)]
                if kept != lines:
                    self.backup(path)
                    if hook.get("created") and not "".join(kept).strip():
                        path.unlink()   # the app made this file for the line alone: remove it again
                    else:
                        path.write_text("".join(kept), encoding="utf-8")
                    changed.append(path)
            self.state["hooks"].remove(hook)
        if run_restore:
            self.run_restore()
        return changed

    def remember_call(self, key, func, args, what):
        """Like remember_cmd, but the undo is a Python function ("module:function"), for
        things that have no command line (Windows wallpapers, a JSON key). First apply wins."""
        if not any(e["key"] == key for e in self.state["restore"]):
            self.state["restore"].append({"key": key, "py": func, "args": list(args), "what": what})

    def run_restore(self):
        """Put live settings back (colour scheme, wallpaper, reloads). Runs last, once every file is back."""
        import importlib
        import subprocess
        for e in list(self.state["restore"]):
            try:
                if "py" in e:
                    module, func = e["py"].split(":")
                    getattr(importlib.import_module(module), func)(*e["args"])
                else:
                    subprocess.run(e["argv"], capture_output=True, text=True, timeout=30)
            except Exception:   # one failing undo must not stop the others
                pass
            self.state["restore"].remove(e)
        if getattr(self, "_broadcast", False):
            from . import platform
            platform.broadcast_settings_change()
            self._broadcast = False


# Comment styles per file format
def hash_comment(text):
    return f"# {text}"


def lua_comment(text):
    return f"-- {text}"


def css_comment(text):
    return f"/* {text} */"
