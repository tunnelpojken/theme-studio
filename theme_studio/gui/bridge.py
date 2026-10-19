"""Python <-> QML bridge. Everything the window can do goes through here, using the
same core/sources/targets code as the CLI, so the GUI can't drift from it."""
import contextlib
import io
import threading
import types
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase

from .. import cli
from ..core.safewrite import Session
from .. import targets as targets_mod
from ..core import config as config_mod
from ..core.color import contrast, to_oklch
from ..core.contrast import report
from ..core.palette import ANSI, Palette, slugify
from ..sources import llm

ROLES = ["primary", "secondary", "tertiary", "error", "surface", "variant", "hover",
         "outline", "shadow", "on_surface", "on_variant"]


class _Log(io.TextIOBase):
    """Collects prints from the CLI functions and forwards them line by line."""

    def __init__(self, emit):
        self.emit, self.buf = emit, ""

    def write(self, s):
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line.strip():
                self.emit(line)
        return len(s)


def _pick_font(candidates, fallback):
    families = set(QFontDatabase.families())
    for f in candidates:
        if f in families:
            return f
    return fallback


class Bridge(QObject):
    paletteChanged = Signal()
    imagesChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()
    logLine = Signal(str)
    targetsChanged = Signal()
    backendChanged = Signal()
    nameChanged = Signal()
    savedChanged = Signal()
    _done = Signal(object, object, str)   # palette, images, error  (worker -> UI thread)

    def __init__(self):
        super().__init__()
        self.cfg = config_mod.load()
        self._palette = None
        self._images = []
        self._busy = False
        self._status = "STANDBY"
        self._name = ""
        self._name_auto = True    # follows the first wallpaper / generated title until the user edits it
        self._saved = False
        self._light = False       # DARK / LIGHT switch in the INPUT panel
        self._backend_ok = None
        self._backend_text = f"{self.cfg.backend.kind.upper()} // {self.cfg.backend.model}" \
            if self.cfg.backend.kind != "none" else "NO MODEL // IMAGE + PRESET ONLY"
        self._targets = [{"name": t.name, "description": t.description, "detected": t.detect(),
                          "checked": t.detect()} for t in targets_mod.ALL.values()]
        self._done.connect(self._finish)
        self.headFont = _pick_font(["Orbitron"], "sans-serif")
        self.monoFont = _pick_font(["ShureTechMono Nerd Font Mono", "ShureTechMono Nerd Font",
                                    "Share Tech Mono", "JetBrains Mono", "DejaVu Sans Mono"], "monospace")

    # ------------------------------------------------------------- properties
    def _get_palette(self):
        if not self._palette:
            return {}
        p = self._palette
        d = {r: p[r] for r in ROLES}
        d.update(title=p.title, note=p.note, normal=list(p.normal), bright=list(p.bright))
        return d
    palette = Property("QVariantMap", _get_palette, notify=paletteChanged)

    def _get_checks(self):
        if not self._palette:
            return []
        rows = report(self._palette, text_min=self.cfg.text_min, accent_min=self.cfg.accent_min)
        return [{"label": r[0], "ratio": round(r[3], 1), "min": r[4], "ok": r[5]} for r in rows]
    checks = Property("QVariantList", _get_checks, notify=paletteChanged)

    def _get_images(self):
        return [QUrl.fromLocalFile(str(i)).toString() for i in self._images]
    images = Property("QVariantList", _get_images, notify=imagesChanged)

    busy = Property(bool, lambda self: self._busy, notify=busyChanged)
    status = Property(str, lambda self: self._status, notify=statusChanged)
    targets = Property("QVariantList", lambda self: self._targets, notify=targetsChanged)
    backendText = Property(str, lambda self: self._backend_text, notify=backendChanged)
    backendOk = Property(int, lambda self: -1 if self._backend_ok is None else int(self._backend_ok),
                         notify=backendChanged)
    hasModel = Property(bool, lambda self: self.cfg.backend.kind != "none", constant=True)
    themesDir = Property(str, lambda self: str(self.cfg.themes).replace(str(Path.home()), "~"), constant=True)
    saved = Property(bool, lambda self: self._saved, notify=savedChanged)
    lightChanged = Signal()
    light = Property(bool, lambda self: self._light, notify=lightChanged)

    @Slot(bool)
    def setLight(self, on):
        if on != self._light:
            self._light = on
            self.lightChanged.emit()

    fontHead = Property(str, lambda self: self.headFont, constant=True)
    fontMono = Property(str, lambda self: self.monoFont, constant=True)

    def _get_name(self):
        return self._name

    @Slot(str)
    def setName(self, name):
        self._name_auto = not name.strip()
        self._set_name(name)

    def _set_name(self, name):
        name = slugify(name) if name.strip() else ""
        if name != self._name:
            self._name = name
            self._saved = False
            self.nameChanged.emit()
            self.savedChanged.emit()
    name = Property(str, _get_name, notify=nameChanged)

    @Slot(result="QVariantList")
    def presets(self):
        return sorted(cli.preset_files())

    @Slot(result="QVariantList")
    def themes(self):
        d = self.cfg.themes
        return sorted(x.name for x in d.iterdir() if x.is_dir() and not x.name.startswith(".")) if d.is_dir() else []

    # ------------------------------------------------------------- helpers
    def _set_status(self, s):
        self._status = s
        self.statusChanged.emit()

    def _set_busy(self, b):
        self._busy = b
        self.busyChanged.emit()

    def _log(self, line):
        self.logLine.emit(str(line).replace(str(Path.home()), "~"))

    def _selected(self):
        return [targets_mod.ALL[t["name"]] for t in self._targets if t["checked"]]

    # ------------------------------------------------------------- images
    @Slot("QVariantList")
    def addImages(self, urls):
        for u in urls:
            path = Path(QUrl(u).toLocalFile() if "://" in str(u) else str(u))
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp") and path.is_file() \
                    and path not in self._images:
                self._images.append(path)
        if self._images and self._name_auto:
            self._set_name(cli.short_name(self._images[0].stem))
        self.imagesChanged.emit()

    @Slot(int)
    def removeImage(self, i):
        if 0 <= i < len(self._images):
            self._images.pop(i)
            if self._name_auto:
                self._set_name(cli.short_name(self._images[0].stem) if self._images else "")
            self.imagesChanged.emit()

    @Slot(int)
    def promote(self, i):
        """Make image i the main monitor's wallpaper (wp1)."""
        if 0 < i < len(self._images):
            self._images.insert(0, self._images.pop(i))
            self.imagesChanged.emit()

    # ------------------------------------------------------------- open a finished theme
    @Slot(str)
    def openTheme(self, name):
        """Load a theme from the themes folder to edit it: its colours, name and wallpapers."""
        if self._busy or not name:
            return
        try:
            p = cli.load_theme(self.cfg, name)
        except (ValueError, OSError, KeyError) as e:
            self._log(f"Can't open {name}: {e}")
            return
        folder = self.cfg.themes / name
        self._images = [folder / f for f in ("wp1.png", "wp2.png") if (folder / f).exists()]
        self.imagesChanged.emit()
        self._light = not p.dark
        self.lightChanged.emit()
        self._palette = p
        self._name, self._name_auto = name, False
        self._saved = True          # nothing changed yet; editing a colour arms CREATE FILES
        self.nameChanged.emit()
        self.savedChanged.emit()
        self.paletteChanged.emit()
        self._set_status("THEME LOADED")
        self._log(f"Opened {name}{' (rebuilt from its Noctalia palette)' if not (folder / 'palette.json').exists() else ''}. "
                  "Click a swatch to change it, then OVERWRITE THEME and APPLY NOW.")

    # ------------------------------------------------------------- generate
    @Slot(str, bool, str)
    def generate(self, prompt, use_ai, preset):
        if self._busy:
            return
        prompt = prompt.strip()
        if not (self._images or prompt or preset):
            self._log("Nothing to work from: drop a wallpaper, write a prompt or pick a preset.")
            return
        use_ai = False   # wallpapers always use the rules; the model is for directives alone
        if prompt and not self._images and not preset and self.cfg.backend.kind == "none":
            self._log("A prompt needs a model. Set [backend] in config.toml (theme-studio init).")
            return
        args = types.SimpleNamespace(
            preset=preset or None, palette=None, image=[str(i) for i in self._images] if not preset else None,
            prompt=prompt or None, ai=use_ai, name=None if self._name_auto else self._name, title=None, accent=None,
            fix=False, no_fix=False, light=self._light)
        self._set_busy(True)
        model = bool(prompt and not self._images and not preset)
        self._set_status("MAGI DELIBERATING" if model else "PATTERN ANALYSIS")
        images = list(self._images) if not preset else []

        def work():
            err, p = "", None
            out = _Log(self._log)   # prints from the CLI code show up in the window's log
            try:
                with contextlib.redirect_stdout(out):
                    p, _imgs, notes = cli.palette_from_args(args, self.cfg)
                    cli.show_fixes(notes)
            except SystemExit as e:
                err = str(e.code) if e.code not in (None, 0) else "stopped"
            except Exception as e:   # never take the window down
                err = f"{type(e).__name__}: {e}"
            self._done.emit(p, images, err)
        threading.Thread(target=work, daemon=True).start()

    def _finish(self, p, images, err):
        self._set_busy(False)
        if err:
            self._log(err)
            self._set_status("PATTERN REJECTED")
            return
        self._palette = p
        self._name = p.name
        self._saved = False
        self.nameChanged.emit()
        self.savedChanged.emit()
        self.paletteChanged.emit()
        self._set_status("PATTERN ACCEPTED")
        self._log(f"{p.title}: palette ready. Click any swatch to adjust it.")

    # ------------------------------------------------------------- editing
    @Slot(str, str)
    def setColor(self, role, hexcol):
        if not self._palette:
            return
        hexcol = hexcol.lower()[:7]
        d = dict(self._palette.__dict__)
        if role.startswith(("normal", "bright")):
            group, i = role.split(":")
            arr = list(d[group])
            arr[int(i)] = hexcol
            d[group] = arr
        else:
            d[role] = hexcol
        try:
            self._palette = Palette.from_dict(d)
        except ValueError as e:
            self._log(str(e))
            return
        self._saved = False
        self.savedChanged.emit()
        self.paletteChanged.emit()

    @Slot()
    def fixContrast(self):
        if not self._palette:
            return
        from ..core.contrast import fix
        self._palette, changes = fix(self._palette, text_min=self.cfg.text_min, accent_min=self.cfg.accent_min)
        for role, a, b in changes:
            self._log(f"contrast fix: {role} {a} -> {b}")
        if not changes:
            self._log("All contrast checks already pass.")
        self.paletteChanged.emit()

    @Slot(str, result=str)
    def textOn(self, bg):
        """Readable text colour for a swatch label."""
        return "#06090d" if contrast(bg, "#06090d") > contrast(bg, "#f2f6f8") else "#f2f6f8"

    @Slot(str, result=float)
    def lightness(self, hexcol):
        return to_oklch(hexcol)[0]

    # ------------------------------------------------------------- targets
    @Slot(str, bool)
    def setTarget(self, name, checked):
        for t in self._targets:
            if t["name"] == name:
                t["checked"] = checked
        self.targetsChanged.emit()

    @Slot(result="QVariantList")
    def plannedFiles(self):
        if not self._palette or not self._name:
            return []
        p = self._named()
        folder, plan = cli.plan_for(p, self.cfg, self._selected(), self._images)
        files = list(plan) + ([folder / f for f in ("wp1.png", "wp2.png", "preview.png")] if self._images else [])
        home = str(Path.home())
        return [{"path": str(f).replace(home, "~"), "exists": f.exists()} for f in files]

    def _named(self):
        p = self._palette
        if self._name and self._name != p.name:
            from ..core.palette import camel
            p = Palette.from_dict({**p.__dict__, "name": self._name, "palette": camel(self._name)})
        return p

    def exists(self):
        return bool(self._name) and (self.cfg.themes / self._name).is_dir()
    nameExists = Property(bool, exists, notify=savedChanged)

    # ------------------------------------------------------------- create / apply
    @Slot(bool)
    def create(self, overwrite):
        if not self._palette or not self._name:
            return
        p = self._named()
        selected = self._selected()
        if not selected:
            self._log("No targets ticked.")
            return
        if self.exists() and not overwrite:
            self._log(f"'{self._name}' already exists. Rename it, or confirm the overwrite.")
            return
        if overwrite and self.exists():
            # Keep the old folder: hand-made themes have files Theme Studio would replace
            import shutil, time
            keep = self.cfg.data / "backups" / time.strftime("%Y%m%d-%H%M%S") / "themes" / self._name
            shutil.copytree(self.cfg.themes / self._name, keep, dirs_exist_ok=True)
            pal = self.cfg.noctalia_palettes / f"{p.palette}.json"   # lives outside the theme folder
            if pal.exists():
                shutil.copy2(pal, keep / pal.name)
            self._log(f"Old version kept in {keep}")
        with contextlib.redirect_stdout(_Log(self._log)):
            cli.write_theme(p, self.cfg, selected, self._images, overwrite)
        self._palette = p
        self._saved = True
        self.savedChanged.emit()
        self._set_status("THEME DEPLOYED")
        self._log(f"Created {self.cfg.themes / p.name}")

    @Slot(result="QVariantList")
    def applyPlan(self):
        """What APPLY will do, for the confirm dialog. Keeps the actions until confirmApply."""
        if not self._saved:
            self._log("Create the files first.")
            return []
        try:
            self._pending = cli.apply_actions(self._name, self.cfg, self._selected())
        except SystemExit as e:
            self._log(str(e.code))
            return []
        home = str(Path.home())
        return [{"text": a.describe.replace(home, "~"), "user": a.touches_user_file} for a in self._pending[0]]

    @Slot()
    def confirmApply(self):
        pending, self._pending = getattr(self, "_pending", None), None
        if not pending:
            return
        with contextlib.redirect_stdout(_Log(self._log)):
            failed = cli.run_actions(pending[0], pending[1], self.cfg)
        self._set_status("SYNCHRONISED" if not failed else "PARTIAL SYNC")

    # ------------------------------------------------------------- undo
    @Slot(result="QVariantList")
    def unhookPlan(self):
        """What RESTORE ORIGINAL will undo, for the confirm dialog."""
        lines = cli.unhook_plan(Session(self.cfg.data))
        if not lines:
            self._log("Nothing to undo: Theme Studio hasn't changed any of your configs.")
        home = str(Path.home())
        return [{"text": l.replace(home, "~"), "user": not l.startswith("delete ")} for l in lines]

    @Slot()
    def confirmUnhook(self):
        try:
            with contextlib.redirect_stdout(_Log(self._log)):
                backups = cli.unhook_run(Session(self.cfg.data))
        except Exception as e:   # never take the window down
            self._log(f"Undo failed: {type(e).__name__}: {e}")
            self._set_status("RESTORE FAILED")
            return
        self._log("Restored: your configs are back to how they were before Theme Studio.")
        if backups:
            self._log(f"Backups: {backups}")
        self._set_status("ORIGINAL RESTORED")

    # ------------------------------------------------------------- backend
    @Slot()
    def testBackend(self):
        def work():
            try:
                msg, ok = llm.test(self.cfg.backend), True
            except llm.BackendError as e:
                msg, ok = str(e), False
            self._backend_ok = ok
            self._backend_text = (f"{self.cfg.backend.kind.upper()} // {self.cfg.backend.model}"
                                  if ok else "OFFLINE")
            self.backendChanged.emit()
            self._log(msg)
        threading.Thread(target=work, daemon=True).start()
