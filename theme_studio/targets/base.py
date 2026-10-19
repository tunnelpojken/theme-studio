"""Target interface.

A target turns a Palette into files and knows how to switch to them.
Neither step does anything by itself: `plan` returns {path: text} and
`apply` returns a list of Actions, so the CLI and GUI can show exactly what
will happen before asking.
"""
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class Action:
    describe: str                 # one line shown before asking
    run: Callable[[], None]
    touches_user_file: bool = False


class Target:
    name = "base"
    description = ""

    def detect(self):
        """True if this app looks installed on this machine."""
        return False

    def plan(self, p, cfg, folder):
        """Return {Path: text} for this palette. `folder` is the theme's folder."""
        return {}

    def apply(self, p, cfg, folder, session):
        """Return the Actions that make this theme active for this app."""
        return []


def session_is(name):
    """True if the running desktop session is `name` (e.g. "KDE", "Hyprland")."""
    import os
    desktops = os.environ.get("XDG_CURRENT_DESKTOP", "") + ":" + os.environ.get("DESKTOP_SESSION", "")
    if name == "Hyprland" and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return True
    return name.lower() in desktops.lower()


def on_path(cmd):
    return shutil.which(cmd) is not None


def exists(path):
    return Path(path).expanduser().exists()


def home(path):
    return Path.home() / path


def run(*cmd, quiet=True):
    """Run a command if it exists; never raise. Returns the CompletedProcess or None."""
    if not shutil.which(cmd[0]):
        return None
    try:
        return subprocess.run(cmd, capture_output=quiet, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None


def signal(process, sig):
    """Send a signal to every process with this exact name (pkill -x)."""
    run("pkill", f"-{sig}", "-x", process)
