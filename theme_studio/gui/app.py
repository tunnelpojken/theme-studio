"""Start the Theme Studio window: theme-studio gui  (or theme-studio-gui)."""
import os
import sys
from pathlib import Path


def main():
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication, QIcon
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
    except ImportError:
        sys.exit("The GUI needs PySide6. Install it with:  pipx install '.[gui]' --force")

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Theme Studio")
    app.setOrganizationName("theme-studio")
    app.setDesktopFileName("theme-studio")       # Wayland app-id: windowrule class:theme-studio
    QQuickStyle.setStyle("Basic")
    icon = Path(__file__).with_name("theme-studio.svg")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))     # title bar / taskbar, even before the icon is installed

    from .bridge import Bridge
    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studio", bridge)
    qml = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        sys.exit("Couldn't load the interface (see the QML errors above).")
    if bridge.hasModel:
        bridge.testBackend()
    code = app.exec()
    del engine          # drop the QML first, so bindings don't fire against a deleted bridge
    sys.exit(code)


if __name__ == "__main__":
    main()
