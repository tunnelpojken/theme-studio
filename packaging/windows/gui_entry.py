"""Entry point of the frozen Windows app: Theme Studio.exe (no console window).

With no console, a failed start would vanish without a word, so the error is written to
%LOCALAPPDATA%\\theme-studio\\gui-error.log and shown in a message box.
"""
import sys
import traceback


def _report(text):
    from theme_studio.core import platform
    log = platform.data_dir() / "gui-error.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(text, encoding="utf-8")
    except OSError:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f"{text[-1500:]}\n\nSaved to {log}",
                                         "Theme Studio couldn't start", 0x10)
    except Exception:
        pass


class _Errors:
    """Collects what the app prints to stderr (Qt's QML errors) so a failure can show it."""
    def __init__(self):
        self.text = []

    def write(self, s):
        self.text.append(s)
        return len(s)

    def flush(self):
        pass


errors = _Errors()
if sys.stderr is None:          # no console: keep Python's messages
    sys.stderr = errors
try:                            # and Qt's (QML load errors come from C++, not Python)
    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(lambda mode, ctx, msg: errors.write(msg + "\n"))
except ImportError:
    pass

try:
    from theme_studio.gui.app import main
    main()
except SystemExit as e:
    if e.code not in (None, 0):
        _report("".join(errors.text) + (e.code if isinstance(e.code, str) else f"exit code {e.code}"))
    raise
except Exception:
    _report("".join(errors.text) + traceback.format_exc())
    raise
