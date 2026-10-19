# PyInstaller build of Theme Studio for Windows: one folder holding
#   Theme Studio.exe   the window (no console)
#   theme-studio.exe   the command line
# Built by build.ps1; run on Windows (PyInstaller doesn't cross-compile).
import os
import re
from PyInstaller.utils.hooks import collect_data_files

ICON = os.path.join(SPECPATH, "theme-studio.ico")
DATAS = collect_data_files("theme_studio")          # presets, templates, QML, icon
# Undo calls these by name ("module:function"), so the analysis can't see them
HIDDEN = ["theme_studio.targets.windows_wallpaper", "theme_studio.targets.windows_terminal"]

gui = Analysis([os.path.join(SPECPATH, "gui_entry.py")], datas=DATAS,
               hiddenimports=HIDDEN + ["PySide6.QtSvg", "PySide6.QtQuickControls2"],
               excludes=["tkinter"])
cli = Analysis([os.path.join(SPECPATH, "cli_entry.py")], datas=DATAS,
               hiddenimports=HIDDEN, excludes=["tkinter"])

# PySide6's hooks copy every QML module Qt ships (a 195 MB web engine, 3D, charts,
# maps...). Theme Studio only uses QtQuick, Controls (Basic style), Layouts, Dialogs
# and Svg, so the rest is left out. ~520 MB -> ~150 MB.
UNUSED = re.compile(
    r"WebEngine|WebChannel|WebView|WebSockets|Qt6?3D|Quick3D|Charts|DataVisualization|Graphs"
    r"|Location|Positioning|Multimedia|SpatialAudio|Pdf|Wayland|TextToSpeech|Scxml|StateMachine"
    r"|Sensors|VirtualKeyboard|RemoteObjects|Bluetooth|Nfc|SerialPort|HttpServer|Designer"
    r"|Qt6?Help|Qt6?Sql|Qt6?Test|qml.QtTest|Qt5Compat|LabsStyleKit|ShaderTools"
    r"|QuickControls2(Material|Universal|Imagine|Fusion|FluentWinUI3|Windows|MacOS|IOS)"
    r"|Controls.(Material|Universal|Imagine|Fusion|FluentWinUI3|Windows|macOS|iOS)", re.I)


def trim(toc):
    return [entry for entry in toc if not UNUSED.search(entry[0].replace("\\", "/"))]


for a in (gui, cli):
    a.binaries, a.datas = trim(a.binaries), trim(a.datas)

gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True, name="Theme Studio",
              console=False, icon=ICON)
cli_exe = EXE(PYZ(cli.pure), cli.scripts, [], exclude_binaries=True, name="theme-studio",
              console=True, icon=ICON)

COLLECT(gui_exe, gui.binaries, gui.datas, cli_exe, cli.binaries, cli.datas,
        name="Theme Studio")
