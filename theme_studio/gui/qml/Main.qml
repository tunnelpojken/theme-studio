// Theme Studio — NERV visual configuration terminal
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: win
    width: 1480; height: 920
    minimumWidth: 960; minimumHeight: 640
    visible: true
    title: "Theme Studio"
    color: ui.bg

    // ------------------------------------------------------------------ look
    QtObject {
        id: ui
        readonly property color bg: "#04080c"
        readonly property color panel: "#08121b"
        readonly property color panel2: "#0c1925"
        readonly property color line: "#183044"
        readonly property color lineHi: "#2a4e66"
        readonly property color cyan: "#9fd8e8"
        readonly property color cyanDim: "#4f7f92"
        readonly property color text: "#d6ecf2"
        readonly property color dim: "#7b97a8"
        readonly property color faint: "#3f5a6b"
        readonly property color amber: "#e8a262"
        readonly property color red: "#e0503c"
        readonly property color green: "#6fd6a0"
        readonly property string head: studio.fontHead
        readonly property string mono: studio.fontMono
    }

    // palette shown in the preview (NERV defaults until a pattern exists)
    readonly property var p: studio.palette
    readonly property bool hasP: p && p.primary !== undefined
    readonly property var fallback: ({
        primary: "#9fd8e8", secondary: "#7ecfcf", tertiary: "#e8a262", error: "#e0503c",
        surface: "#060d14", variant: "#0d1b2a", hover: "#15283a", outline: "#24405a", shadow: "#020406",
        on_surface: "#daeef0", on_variant: "#8fb4c6", title: "", note: "",
        normal: ["#0d1b2a", "#e0503c", "#6fd6a0", "#e8c46a", "#6aa8e8", "#b48ae8", "#9fd8e8", "#daeef0"],
        bright: ["#3a5468", "#f06a58", "#92e6bc", "#f2d68e", "#90c0f0", "#cfa8f0", "#c2ecf4", "#ffffff"] })
    function c(role) { return hasP && p[role] !== undefined ? p[role] : fallback[role] }
    function ansi(group, i) { return hasP ? p[group][i] : fallback[group][i] }

    readonly property bool roomy: width >= 1500 && height >= 940
    property var files: []
    function refreshFiles() { files = studio.plannedFiles() }
    property bool confirmOverwrite: false

    Connections {
        target: studio
        function onPaletteChanged() { win.refreshFiles(); win.confirmOverwrite = false }
        function onNameChanged() { win.refreshFiles(); win.confirmOverwrite = false }
        function onTargetsChanged() { win.refreshFiles() }
        function onImagesChanged() { win.refreshFiles() }
        function onSavedChanged() { win.refreshFiles() }
        function onLogLine(line) {
            logModel.append({ t: Qt.formatTime(new Date(), "hh:mm:ss"), line: line })
            logView.positionViewAtEnd()
        }
    }
    ListModel { id: logModel }

    // ------------------------------------------------------------------ components
    component Mono: Text {
        font.family: ui.mono; font.pixelSize: 13; color: ui.text
    }
    component Head: Text {
        font.family: ui.head; font.pixelSize: 13; font.letterSpacing: 2.5; font.weight: Font.DemiBold
        color: ui.cyan
    }

    // Panel with an index tag, title, rule and corner brackets
    component Panel: Rectangle {
        id: panelRoot
        property string tag: "01"
        property string title: ""
        property string sub: ""
        default property alias content: body.data
        color: ui.panel
        border.color: ui.line; border.width: 1

        Repeater {   // corner brackets
            model: 4
            Item {
                width: 12; height: 12
                x: index % 2 ? panelRoot.width - 13 : 1
                y: index > 1 ? panelRoot.height - 13 : 1
                Rectangle { width: 12; height: 2; color: ui.cyan; y: index > 1 ? 10 : 0 }
                Rectangle { width: 2; height: 12; color: ui.cyan; x: index % 2 ? 10 : 0 }
            }
        }
        RowLayout {
            id: header
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 18 }
            spacing: 10
            Rectangle {
                implicitWidth: idx.implicitWidth + 12; implicitHeight: 20; color: ui.amber
                Text { id: idx; anchors.centerIn: parent; text: panelRoot.tag
                       font.family: ui.mono; font.pixelSize: 12; font.bold: true; color: ui.bg }
            }
            Head { text: panelRoot.title; font.pixelSize: 15 }
            Rectangle { Layout.fillWidth: true; height: 1; color: ui.line }
            Mono { text: panelRoot.sub; color: ui.faint; font.pixelSize: 11 }
        }
        Item {
            id: body
            anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom
                      leftMargin: 18; rightMargin: 18; topMargin: 14; bottomMargin: 18 }
        }
    }

    component NervButton: AbstractButton {
        id: btn
        property color accent: ui.cyan
        property bool big: false
        property bool solid: false
        implicitHeight: big ? 48 : 32
        implicitWidth: label.implicitWidth + 32
        hoverEnabled: true
        opacity: enabled ? 1 : 0.35
        // NERV plate: top-right and bottom-left corners cut at 45°
        background: Canvas {
            id: plate
            property color fill: btn.solid ? (btn.down ? Qt.darker(btn.accent, 1.3) : btn.hovered ? Qt.lighter(btn.accent, 1.12) : btn.accent)
                                           : (btn.down ? Qt.rgba(btn.accent.r, btn.accent.g, btn.accent.b, 0.25)
                                                       : btn.hovered ? Qt.rgba(btn.accent.r, btn.accent.g, btn.accent.b, 0.12) : Qt.rgba(0, 0, 0, 0))
            onFillChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d"), w = width, h = height, k = btn.big ? 12 : 8
                ctx.reset()
                ctx.beginPath()
                ctx.moveTo(0.5, 0.5); ctx.lineTo(w - k, 0.5); ctx.lineTo(w - 0.5, k)
                ctx.lineTo(w - 0.5, h - 0.5); ctx.lineTo(k, h - 0.5); ctx.lineTo(0.5, h - k); ctx.closePath()
                ctx.fillStyle = fill; ctx.fill()
                ctx.lineWidth = 1; ctx.strokeStyle = btn.accent; ctx.stroke()
            }
        }
        contentItem: Text {
            id: label
            text: btn.text
            font.family: ui.head; font.pixelSize: btn.big ? 14 : 11; font.letterSpacing: 2; font.weight: Font.DemiBold
            color: btn.solid ? ui.bg : btn.accent
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }

    component NervCheck: AbstractButton {
        id: chk
        checkable: true
        property string sub: ""
        property bool tagged: false
        property bool compact: false
        hoverEnabled: true
        implicitHeight: compact ? 24 : (sub ? 40 : 26)
        ToolTip.visible: compact && hovered && sub !== ""
        ToolTip.text: sub
        ToolTip.delay: 400
        contentItem: RowLayout {
            spacing: 10
            Rectangle {
                Layout.alignment: chk.compact ? Qt.AlignVCenter : Qt.AlignTop; Layout.topMargin: chk.compact ? 0 : 2
                implicitWidth: 14; implicitHeight: 14; color: "transparent"
                border.color: chk.checked ? ui.cyan : chk.hovered ? ui.cyanDim : ui.lineHi; border.width: 1
                Rectangle { anchors.fill: parent; anchors.margins: 3; color: ui.cyan; visible: chk.checked }
            }
            ColumnLayout {
                spacing: 1; Layout.fillWidth: true
                RowLayout {
                    Layout.fillWidth: true
                    Mono { text: chk.text.toUpperCase(); color: chk.checked ? ui.text : ui.dim; font.pixelSize: 13 }
                    Item { Layout.fillWidth: true; visible: chk.compact }
                    Mono { text: chk.tagged ? "DETECTED" : "—"; visible: chk.compact || chk.tagged
                           color: chk.tagged ? ui.green : ui.faint; font.pixelSize: 9; font.letterSpacing: 1.5 }
                }
                Mono { text: chk.sub; visible: chk.sub !== "" && !chk.compact; color: ui.faint; font.pixelSize: 11
                       elide: Text.ElideRight; Layout.fillWidth: true }
            }
        }
    }

    // A palette swatch you can click to edit
    component Swatch: Item {
        id: sw
        property string role: ""
        property string label: role
        property color value: "black"
        property bool compact: false
        implicitHeight: compact ? 26 : (win.roomy ? 46 : 38)
        implicitWidth: compact ? 26 : 150
        Rectangle {
            id: chip
            width: sw.compact ? sw.width : (win.roomy ? 40 : 32); height: sw.compact ? sw.height : (win.roomy ? 40 : 32)
            color: sw.value
            border.color: hover.containsMouse ? ui.cyan : ui.line; border.width: hover.containsMouse ? 2 : 1
        }
        Column {
            visible: !sw.compact
            anchors { left: chip.right; leftMargin: 10; verticalCenter: chip.verticalCenter }
            Mono { text: sw.label; font.pixelSize: 12; color: ui.text }
            Mono { text: String(sw.value); font.pixelSize: 11; color: ui.dim }
        }
        MouseArea {
            id: hover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            enabled: win.hasP
            onClicked: picker.edit(sw.role, String(sw.value), sw.label)
        }
        ToolTip.visible: sw.compact && hover.containsMouse
        ToolTip.text: sw.label + "  " + sw.value
    }

    // Hexagon outline, the NERV logo motif
    component Hex: Canvas {
        property color stroke: ui.cyan
        property real lw: 1.5
        onStrokeChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var r = Math.min(width, height) / 2 - lw, cx = width / 2, cy = height / 2
            ctx.beginPath()
            for (var i = 0; i < 6; i++) {
                var a = Math.PI / 3 * i + Math.PI / 6
                var x = cx + r * Math.cos(a), y = cy + r * Math.sin(a)
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
            }
            ctx.closePath(); ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke()
        }
    }

    // Everything is laid out for 1280x860 or more. On smaller screens (1366x768 laptops,
    // VMs) the whole view scales down evenly instead of cutting off the bottom buttons.
    Item {
        id: stage
        readonly property real k: Math.min(1, win.width / 1280, win.height / 860)
        width: win.width / k; height: win.height / k
        scale: k; transformOrigin: Item.TopLeft

        // ------------------------------------------------------------------ header
        Rectangle {
            id: top
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: 64; color: ui.bg
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: ui.line }
            Rectangle { anchors.bottom: parent.bottom; width: 220; height: 2; color: ui.amber }

            RowLayout {
                anchors { fill: parent; leftMargin: 20; rightMargin: 20 }
                spacing: 14
                Item {
                    implicitWidth: 38; implicitHeight: 38
                    Hex { anchors.fill: parent; stroke: ui.cyan; lw: 2 }
                    Hex { anchors.fill: parent; anchors.margins: 9; stroke: ui.amber; lw: 1.5 }
                }
                ColumnLayout {
                    spacing: 0
                    Text { text: "THEME STUDIO"; font.family: ui.head; font.pixelSize: 22; font.letterSpacing: 6
                           font.weight: Font.Bold; color: ui.text }
                    Mono { text: "NERV // VISUAL CONFIGURATION SYSTEM  ·  SUPERVISOR: FESTED"; color: ui.faint
                           font.pixelSize: 10; font.letterSpacing: 2 }
                }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    spacing: 2
                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        spacing: 8
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: studio.busy ? ui.amber : studio.status.indexOf("REJECTED") >= 0 ? ui.red : ui.green
                            SequentialAnimation on opacity {
                                running: studio.busy; loops: Animation.Infinite
                                NumberAnimation { to: 0.2; duration: 450 } NumberAnimation { to: 1; duration: 450 }
                            }
                        }
                        Head { text: "STATUS: " + studio.status; font.pixelSize: 12
                               color: studio.busy ? ui.amber : ui.cyan }
                    }
                    Mono { Layout.alignment: Qt.AlignRight; text: studio.themesDir; color: ui.faint; font.pixelSize: 10 }
                }
            }
        }

        // ------------------------------------------------------------------ body
        RowLayout {
            anchors { left: parent.left; right: parent.right; top: top.bottom; bottom: magi.top; margins: 16 }
            spacing: 16

            // ================================================= 01 INPUT
            Panel {
                Layout.preferredWidth: win.roomy ? 360 : 320; Layout.fillHeight: true
                tag: "01"; title: "INPUT"; sub: "SOURCE DATA"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    // Drop zone
                    Rectangle {
                        id: drop
                        Layout.fillWidth: true; Layout.preferredHeight: studio.images.length ? 92 : 150
                        color: dropArea.containsDrag ? Qt.rgba(0.62, 0.85, 0.91, 0.08) : ui.panel2
                        border.color: dropArea.containsDrag ? ui.cyan : ui.lineHi; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 180 } }

                        Grid {   // faint hex grid
                            anchors.fill: parent; anchors.margins: 6; clip: true
                            columns: Math.floor(width / 28); spacing: 4; opacity: 0.09
                            Repeater { model: 40; Hex { width: 24; height: 24; stroke: ui.cyanDim; lw: 1 } }
                        }
                        Rectangle {   // quiet plate behind the label so the grid doesn't fight it
                            anchors.centerIn: parent; width: dropLabel.width + 28; height: dropLabel.height + 16
                            color: ui.panel2; opacity: 0.85
                        }
                        Column {
                            id: dropLabel
                            anchors.centerIn: parent; spacing: 4
                            Head { anchors.horizontalCenter: parent.horizontalCenter
                                   text: dropArea.containsDrag ? "RELEASE TO LOAD" : "DROP WALLPAPERS"; font.pixelSize: 14 }
                            Mono { anchors.horizontalCenter: parent.horizontalCenter
                                   text: win.roomy ? "or click to browse  ·  first = main monitor" : "or click to browse"
                                   color: ui.dim; font.pixelSize: 11 }
                        }
                        DropArea {
                            id: dropArea; anchors.fill: parent
                            onDropped: (drop) => { studio.addImages(drop.urls) }
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: fileDialog.open() }
                    }

                    // Loaded images
                    ListView {
                        Layout.fillWidth: true; Layout.preferredHeight: studio.images.length ? 92 : 0
                        visible: studio.images.length > 0
                        orientation: ListView.Horizontal; spacing: 10; clip: true
                        model: studio.images
                        delegate: Item {
                            width: 132; height: 92
                            Rectangle {
                                id: thumb
                                width: 132; height: 74; color: ui.bg
                                border.color: index === 0 ? ui.amber : ui.line; border.width: index === 0 ? 2 : 1
                                Image { anchors.fill: parent; anchors.margins: 2; source: modelData
                                        fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 260 }
                                Rectangle {
                                    anchors { right: parent.right; top: parent.top; margins: 4 }
                                    width: 20; height: 20; color: Qt.rgba(0, 0, 0, 0.7)
                                    Mono { anchors.centerIn: parent; text: "✕"; color: ui.red; font.pixelSize: 12 }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                onClicked: studio.removeImage(index) }
                                }
                                MouseArea {
                                    id: thumbMouse
                                    anchors.fill: parent; z: -1; enabled: index > 0; hoverEnabled: true
                                    cursorShape: index > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: studio.promote(index)
                                    ToolTip.visible: containsMouse && index > 0
                                    ToolTip.text: "Click to make this the main monitor's wallpaper"
                                }
                            }
                            Mono {
                                anchors.top: thumb.bottom; anchors.topMargin: 3
                                text: index === 0 ? "WP1 · MAIN" : index === 1 ? "WP2 · SECOND" : "UNUSED"
                                color: index === 0 ? ui.amber : ui.dim; font.pixelSize: 10
                            }
                        }
                    }

                    // Prompt
                    Head { text: studio.images.length ? "DIRECTIVE  ·  OPTIONAL" : "DIRECTIVE  ·  MAGI"
                           font.pixelSize: 11; color: ui.dim }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 56; Layout.maximumHeight: 150
                        color: ui.panel2; border.color: promptBox.activeFocus ? ui.cyan : ui.line
                        ScrollView {
                            anchors.fill: parent; anchors.margins: 2
                            TextArea {
                                id: promptBox
                                enabled: true
                                placeholderText: studio.images.length
                                    ? "Optional: name colours to steer the wallpaper theme…\ne.g. blood red and gold"
                                    : studio.hasModel
                                    ? "Describe a theme and MAGI designs it…\ne.g. Unit-01: deep purple, lime green, orange"
                                    : "No model configured.\nDrop a wallpaper, or name colours with a preset."
                                placeholderTextColor: ui.faint
                                color: ui.text; font.family: ui.mono; font.pixelSize: 13
                                wrapMode: TextArea.Wrap; background: null
                                selectionColor: ui.cyanDim
                                Keys.onReturnPressed: (e) => {
                                    if (e.modifiers & Qt.ControlModifier) generateBtn.clicked(); else e.accepted = false
                                }
                            }
                        }
                    }
                    // Preset
                    Head { text: "OR LOAD PRESET"; font.pixelSize: 11; color: ui.dim }
                    ComboBox {
                        id: presetBox
                        Layout.fillWidth: true; implicitHeight: 34
                        model: ["—  none  —"].concat(studio.presets())
                        font.family: ui.mono; font.pixelSize: 13
                        background: Rectangle { color: ui.panel2; border.color: presetBox.activeFocus ? ui.cyan : ui.line }
                        contentItem: Mono { leftPadding: 10; text: presetBox.displayText; verticalAlignment: Text.AlignVCenter
                                            color: presetBox.currentIndex > 0 ? ui.text : ui.dim }
                        popup.background: Rectangle { color: ui.panel2; border.color: ui.cyan }
                        delegate: ItemDelegate {
                            width: presetBox.width
                            contentItem: Mono { text: modelData; color: highlighted ? ui.bg : ui.text }
                            highlighted: presetBox.highlightedIndex === index
                            background: Rectangle { color: highlighted ? ui.cyan : "transparent" }
                        }
                    }

                    // Open a finished theme to edit it
                    Head { text: "OR OPEN YOUR THEME"; font.pixelSize: 11; color: ui.dim; Layout.topMargin: 6 }
                    ComboBox {
                        id: themeBox
                        Layout.fillWidth: true; implicitHeight: 34
                        model: ["—  none  —"].concat(studio.themes())
                        font.family: ui.mono; font.pixelSize: 13
                        background: Rectangle { color: ui.panel2; border.color: themeBox.activeFocus ? ui.cyan : ui.line }
                        contentItem: Mono { leftPadding: 10; text: themeBox.displayText; verticalAlignment: Text.AlignVCenter
                                            color: themeBox.currentIndex > 0 ? ui.text : ui.dim }
                        popup.background: Rectangle { color: ui.panel2; border.color: ui.cyan }
                        delegate: ItemDelegate {
                            width: themeBox.width
                            contentItem: Mono { text: modelData; color: highlighted ? ui.bg : ui.text }
                            highlighted: themeBox.highlightedIndex === index
                            background: Rectangle { color: highlighted ? ui.cyan : "transparent" }
                        }
                        onActivated: (i) => {
                            if (i > 0) { presetBox.currentIndex = 0; studio.openTheme(themeBox.textAt(i)) }
                        }
                        // the list follows new themes: refresh it whenever it opens
                        Connections {
                            target: themeBox.popup
                            function onAboutToShow() { themeBox.model = ["—  none  —"].concat(studio.themes()) }
                        }
                    }

                    // Mode: dark or light theme. Switching regenerates the current pattern.
                    Head { text: "MODE"; font.pixelSize: 11; color: ui.dim; Layout.topMargin: 6 }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Repeater {
                            model: [{ label: "DARK", light: false }, { label: "LIGHT", light: true }]
                            Rectangle {
                                required property var modelData
                                readonly property bool on: studio.light === modelData.light
                                Layout.fillWidth: true; implicitHeight: 30
                                color: on ? ui.cyan : (modeArea.containsMouse ? ui.panel2 : "transparent")
                                border.color: on ? ui.cyan : ui.line
                                Mono { anchors.centerIn: parent; text: modelData.label; font.pixelSize: 12
                                       color: parent.on ? ui.bg : ui.text }
                                MouseArea {
                                    id: modeArea
                                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (parent.on) return
                                        studio.setLight(parent.modelData.light)
                                        if (win.hasP && !studio.busy) generateBtn.clicked()
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                    NervButton {
                        id: generateBtn
                        Layout.topMargin: 6
                        Layout.fillWidth: true
                        big: true; solid: true
                        enabled: !studio.busy
                        text: studio.busy ? "ANALYSING…" : (win.hasP ? "REGENERATE PATTERN" : "GENERATE PATTERN")
                        onClicked: studio.generate(promptBox.text, false,
                                                   presetBox.currentIndex > 0 ? presetBox.currentText : "")
                    }
                    Mono { Layout.alignment: Qt.AlignHCenter; text: "Ctrl+Enter generates  ·  Ctrl+O adds wallpapers"
                           color: ui.faint; font.pixelSize: 10; visible: win.roomy }
                }
            }

            // ================================================= 02 ANALYSIS
            Panel {
                Layout.fillWidth: true; Layout.fillHeight: true
                tag: "02"; title: "ANALYSIS"; sub: win.hasP ? c("title").toUpperCase() : "AWAITING PATTERN"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    // ---- mock desktop
                    Rectangle {
                        id: desk
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 200
                        color: c("shadow"); clip: true
                        border.color: ui.line

                        Image {
                            anchors.fill: parent; source: studio.images.length ? studio.images[0] : ""
                            // Fit, not crop: the whole picture stays visible, whatever its shape
                            fillMode: Image.PreserveAspectFit; asynchronous: true
                            sourceSize.width: 1400; sourceSize.height: 1400
                        }
                        Rectangle { anchors.fill: parent; color: c("shadow"); opacity: studio.images.length ? 0.35 : 1 }

                        // bar
                        Rectangle {
                            id: mockBar
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                            height: 34; radius: 8; color: c("surface"); border.color: c("outline")
                            Row {
                                anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                                spacing: 6
                                Repeater {
                                    model: 5
                                    Rectangle {
                                        width: 26; height: 20; radius: 5
                                        color: index === 1 ? c("primary") : c("variant")
                                        Mono { anchors.centerIn: parent; text: index + 1; font.pixelSize: 11; font.bold: index === 1
                                               color: index === 1 ? c("surface") : c("on_variant") }
                                    }
                                }
                            }
                            Mono { anchors.centerIn: parent; text: Qt.formatTime(new Date(), "hh:mm"); font.bold: true
                                   color: c("on_surface") }
                            Row {
                                anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                                spacing: 6
                                Repeater {
                                    model: ["primary", "secondary", "tertiary", "error"]
                                    Rectangle { width: 22; height: 16; radius: 4; color: c("variant")
                                                border.color: c(modelData); border.width: 2 }
                                }
                            }
                        }

                        // kitty window
                        Rectangle {
                            id: term
                            anchors { left: parent.left; top: mockBar.bottom; margins: 12; topMargin: 14 }
                            width: Math.min(parent.width * 0.62, 640)
                            height: Math.min(parent.height - mockBar.height - 40, 250)
                            radius: 10
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: c("primary") }
                                GradientStop { position: 1; color: c("secondary") }
                            }
                            Rectangle {
                                anchors.fill: parent; anchors.margins: 2; radius: 8; color: c("surface"); clip: true
                                Rectangle {
                                    width: parent.width; height: 26; color: c("variant"); radius: 8
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 8; color: c("variant") }
                                    Mono { x: 12; anchors.verticalCenter: parent.verticalCenter; text: "kitty"
                                           color: c("on_variant"); font.pixelSize: 12 }
                                }
                                Column {
                                    x: 14; y: 38; spacing: 5
                                    Repeater {
                                        model: [
                                            [["normal",2,"fested"],["on_surface",0,"@"],["normal",4,"nerv"],["on_surface",0," ~/themes "],["primary",0,"❯ "],["on_surface",0,"ls -la"]],
                                            [["normal",4,"drwxr-xr-x "],["on_variant",0,"  4096 "],["normal",4,"presets/"]],
                                            [["normal",2,"-rwxr-xr-x "],["on_variant",0,"  1287 "],["normal",2,"switch.sh"]],
                                            [["on_surface",0,"-rw-r--r-- "],["on_variant",0,"   412 "],["on_surface",0,"kitty.conf"]],
                                            [["normal",5,"lrwxrwxrwx "],["on_variant",0,"    18 "],["normal",6,"active.lua"],["on_variant",0," -> "],["normal",3,"themes/"]],
                                            [["error",0,"error: "],["on_surface",0,"pattern blue detected in "],["normal",3,"'sector 7'"]],
                                            [["normal",1,"warning: "],["on_surface",0,"sync ratio "],["secondary",0,"41.3%"]],
                                            [["normal",2,"fested"],["on_surface",0,"@"],["normal",4,"nerv"],["on_surface",0," ~/themes "],["primary",0,"❯ "],["on_surface",0,"█"]]
                                        ]
                                        Row {
                                            Repeater {
                                                model: modelData
                                                Mono {
                                                    text: modelData[2]; font.pixelSize: 13
                                                    color: modelData[0] === "normal" ? win.ansi("normal", modelData[1]) : c(modelData[0])
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // empty state
                        Column {
                            visible: !win.hasP
                            anchors { right: parent.right; rightMargin: 40; verticalCenter: parent.verticalCenter }
                            spacing: 10
                            Item {
                                width: 90; height: 90; anchors.horizontalCenter: parent.horizontalCenter
                                Hex { anchors.fill: parent; stroke: ui.cyanDim; lw: 2 }
                                Hex { anchors.fill: parent; anchors.margins: 22; stroke: ui.amber; lw: 1.5
                                      RotationAnimation on rotation { running: studio.busy; loops: Animation.Infinite
                                                                      from: 0; to: 360; duration: 2400 } }
                            }
                            Head { anchors.horizontalCenter: parent.horizontalCenter
                                   text: studio.busy ? studio.status : "NO PATTERN"; color: ui.dim }
                            Mono { anchors.horizontalCenter: parent.horizontalCenter
                                   text: studio.busy ? "stand by" : "awaiting source data"; color: ui.faint; font.pixelSize: 11 }
                        }

                        // busy overlay on an existing palette
                        Rectangle {
                            id: busyVeil
                            anchors.fill: parent; visible: studio.busy && win.hasP; color: Qt.rgba(0.01, 0.03, 0.05, 0.7)
                            Head { anchors.centerIn: parent; text: studio.status; color: ui.amber; font.pixelSize: 16
                                   SequentialAnimation on opacity { running: busyVeil.visible; loops: Animation.Infinite
                                       NumberAnimation { to: 0.3; duration: 500 } NumberAnimation { to: 1; duration: 500 } } }
                        }
                    }

                    // ---- title + swatches
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: win.hasP
                        ColumnLayout {
                            spacing: 2
                            Text { text: c("title"); font.family: ui.head; font.pixelSize: 20; font.letterSpacing: 2
                                   color: ui.text; elide: Text.ElideRight; Layout.maximumWidth: 420 }
                            Mono { text: c("note"); color: ui.dim; font.pixelSize: 12; elide: Text.ElideRight
                                   Layout.maximumWidth: 420 }
                        }
                        Item { Layout.fillWidth: true }
                        Mono { text: "click any colour to adjust"; color: ui.faint; font.pixelSize: 11 }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        visible: win.hasP
                        columns: Math.max(2, Math.floor(width / 150)); rowSpacing: win.roomy ? 8 : 4; columnSpacing: 8
                        Repeater {
                            model: ["primary", "secondary", "tertiary", "error", "surface", "variant",
                                    "hover", "outline", "shadow", "on_surface", "on_variant"]
                            Swatch { role: modelData; label: modelData; value: c(modelData); Layout.fillWidth: true }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; visible: win.hasP; spacing: 12
                        Head { text: "TERMINAL"; font.pixelSize: 10; color: ui.dim; Layout.preferredWidth: 80 }
                        Repeater {
                            model: ["normal", "bright"]
                            Row {
                                id: ansiRow
                                spacing: 3
                                property string group: modelData
                                Repeater {
                                    model: 8
                                    Swatch { compact: true; width: 24; height: 22
                                             role: ansiRow.group + ":" + index
                                             label: ansiRow.group + " " + ["black","red","green","yellow","blue","magenta","cyan","white"][index]
                                             value: win.ansi(ansiRow.group, index) }
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // ---- contrast
                    RowLayout {
                        Layout.fillWidth: true
                        visible: win.hasP
                        spacing: 6
                        Head { text: "BALTHASAR // CONTRAST"; font.pixelSize: 10; color: ui.dim }
                        Mono {
                            property int passed: studio.checks.filter(function (x) { return x.ok }).length
                            text: passed + " / " + studio.checks.length + " PASS"
                            color: passed === studio.checks.length ? ui.green : ui.amber; font.pixelSize: 11
                        }
                        Flow {
                            Layout.fillWidth: true; spacing: 6
                            Repeater {
                                model: studio.checks.filter(function (x) { return !x.ok })
                                Rectangle {
                                    width: chkTxt.implicitWidth + 14; height: 20
                                    color: "transparent"; border.color: modelData.ok ? ui.line : ui.amber
                                    Mono { id: chkTxt; anchors.centerIn: parent; font.pixelSize: 10
                                           text: modelData.label + " " + modelData.ratio
                                           color: modelData.ok ? ui.dim : ui.amber }
                                }
                            }
                        }
                        NervButton {
                            text: "AUTO-FIX"; accent: ui.amber
                            visible: studio.checks.some(function (x) { return !x.ok })
                            onClicked: studio.fixContrast()
                        }
                    }
                }
            }

            // ================================================= 03 DEPLOY
            Panel {
                Layout.preferredWidth: win.roomy ? 380 : 340; Layout.fillHeight: true
                tag: "03"; title: "DEPLOY"; sub: "OUTPUT"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Head { text: "DESIGNATION"; font.pixelSize: 11; color: ui.dim }
                    Rectangle {
                        Layout.fillWidth: true; implicitHeight: 34
                        color: ui.panel2; border.color: nameField.activeFocus ? ui.cyan : studio.nameExists && !studio.saved ? ui.amber : ui.line
                        TextInput {
                            id: nameField
                            anchors.fill: parent; anchors.leftMargin: 10; verticalAlignment: TextInput.AlignVCenter
                            text: studio.name; color: ui.text; font.family: ui.mono; font.pixelSize: 14
                            selectionColor: ui.cyanDim; clip: true
                            onEditingFinished: studio.setName(text)
                        }
                        Mono { anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                               text: studio.saved ? "SAVED" : (studio.name && studio.nameExists ? "EXISTS" : "")
                               color: studio.saved ? ui.green : ui.amber; font.pixelSize: 10; font.letterSpacing: 1.5 }
                    }

                    Head { text: "CASPAR // TARGETS"; font.pixelSize: 11; color: ui.dim; Layout.topMargin: 4 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: win.roomy ? 8 : 2
                        Repeater {
                        model: studio.targets
                        NervCheck {
                            Layout.fillWidth: true
                            compact: true
                            text: modelData.name; sub: modelData.description; tagged: modelData.detected
                            checked: modelData.checked
                            onToggled: studio.setTarget(modelData.name, checked)
                        }
                        }
                    }

                    Head { text: "FILES"; font.pixelSize: 11; color: ui.dim; Layout.topMargin: 4
                           visible: win.files.length > 0 }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 30
                        visible: win.files.length > 0
                        clip: true; model: win.files; spacing: 2
                        ScrollBar.vertical: ScrollBar { }
                        delegate: RowLayout {
                            width: ListView.view.width - 8
                            Mono { text: modelData.exists ? "OVR" : "NEW"; font.pixelSize: 9; font.letterSpacing: 1
                                   color: modelData.exists ? ui.amber : ui.green; Layout.preferredWidth: 28 }
                            Mono { text: modelData.path; font.pixelSize: 10; color: ui.dim; elide: Text.ElideMiddle
                                   Layout.fillWidth: true }
                        }
                    }
                    Item { Layout.fillHeight: true; visible: win.files.length === 0 }

                    NervButton {
                        Layout.fillWidth: true; big: true; solid: true
                        accent: win.confirmOverwrite ? ui.amber : ui.cyan
                        enabled: win.hasP && !studio.busy && studio.name !== "" && !studio.saved
                        text: studio.saved ? "FILES CREATED"
                              : win.confirmOverwrite ? "CONFIRM OVERWRITE"
                              : (studio.nameExists ? "OVERWRITE THEME" : "CREATE FILES")
                        onClicked: {
                            if (studio.nameExists && !win.confirmOverwrite) { win.confirmOverwrite = true; return }
                            studio.create(win.confirmOverwrite)
                            win.confirmOverwrite = false
                        }
                    }
                    NervButton {
                        Layout.fillWidth: true; big: true
                        accent: ui.amber
                        enabled: studio.saved && !studio.busy
                        text: "APPLY NOW"
                        onClicked: { confirmApply.undo = false; confirmApply.items = studio.applyPlan()
                                     if (confirmApply.items.length) confirmApply.open() }
                    }
                    NervButton {
                        // Undo everything Theme Studio ever applied (the GUI's 'theme-studio unhook')
                        Layout.fillWidth: true
                        accent: ui.dim
                        enabled: !studio.busy
                        text: "RESTORE ORIGINAL"
                        onClicked: { confirmApply.undo = true; confirmApply.items = studio.unhookPlan()
                                     if (confirmApply.items.length) confirmApply.open() }
                    }
                }
            }
        }

        // ------------------------------------------------------------------ MAGI bar + log
        Rectangle {
            id: magi
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: win.roomy ? 128 : 100; color: ui.bg
            Rectangle { width: parent.width; height: 1; color: ui.line }

            RowLayout {
                anchors { fill: parent; margins: 16; topMargin: 12 }
                spacing: 16

                Repeater {
                    model: [
                        { name: "MELCHIOR·1", what: "MODEL",
                          state: !studio.hasModel ? 0 : studio.backendOk === 1 ? 1 : studio.backendOk === 0 ? -1 : 0,
                          info: studio.backendText },
                        { name: "BALTHASAR·2", what: "CONTRAST",
                          state: !win.hasP ? 0 : studio.checks.every(function (x) { return x.ok }) ? 1 : -1,
                          info: !win.hasP ? "NO PATTERN" : studio.checks.filter(function (x) { return x.ok }).length + " / " + studio.checks.length + " PASS" },
                        { name: "CASPAR·3", what: "TARGETS",
                          state: studio.targets.some(function (x) { return x.checked }) ? 1 : -1,
                          info: studio.targets.filter(function (x) { return x.checked }).length + " ARMED" }
                    ]
                    Rectangle {
                        Layout.preferredWidth: win.roomy ? 220 : 190; Layout.fillHeight: true
                        color: ui.panel
                        border.color: modelData.state === 1 ? ui.cyanDim : modelData.state === -1 ? ui.amber : ui.line
                        Rectangle {
                            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                            width: 4
                            color: modelData.state === 1 ? ui.cyan : modelData.state === -1 ? ui.amber : ui.faint
                        }
                        Column {
                            anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
                            spacing: 4
                            Head { text: modelData.name; font.pixelSize: 13; color: ui.text }
                            Mono { text: modelData.what; color: ui.faint; font.pixelSize: 10; font.letterSpacing: 2; visible: win.roomy }
                            Head { font.pixelSize: 12
                                   text: modelData.state === 1 ? "APPROVED" : modelData.state === -1 ? "DENIED" : "STANDBY"
                                   color: modelData.state === 1 ? ui.cyan : modelData.state === -1 ? ui.amber : ui.faint }
                            Mono { text: modelData.info; color: ui.dim; font.pixelSize: 10; width: 190; elide: Text.ElideRight }
                        }
                        MouseArea {
                            anchors.fill: parent; visible: index === 0 && studio.hasModel
                            cursorShape: Qt.PointingHandCursor; onClicked: studio.testBackend()
                            ToolTip.visible: containsMouse; hoverEnabled: true; ToolTip.text: "Test the model connection"
                        }
                    }
                }

                // log
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    color: ui.panel; border.color: ui.line
                    ListView {
                        id: logView
                        anchors.fill: parent; anchors.margins: 10
                        clip: true; model: logModel; spacing: 2
                        ScrollBar.vertical: ScrollBar { }
                        delegate: Row {
                            spacing: 10
                            Mono { text: t; color: ui.faint; font.pixelSize: 11 }
                            Mono { text: line; font.pixelSize: 11; width: logView.width - 80; wrapMode: Text.Wrap
                                   color: line.indexOf("error") >= 0 || line.indexOf("rror:") >= 0 || line.indexOf("Not ") === 0 ? ui.amber
                                        : line.indexOf("fix") >= 0 || line.indexOf("tidy") >= 0 ? ui.dim : ui.text }
                        }
                        Mono { visible: logModel.count === 0; text: "> system log empty"; color: ui.faint; font.pixelSize: 11 }
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------------ dialogs
    FileDialog {
        id: fileDialog
        title: "Select wallpapers"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        onAccepted: studio.addImages(selectedFiles)
    }

    // NERV colour picker
    Popup {
        id: picker
        objectName: "picker"
        property string role: ""
        property string label: ""
        property string original: "#000000"
        property real h: 0
        property real s: 0
        property real v: 0
        readonly property color current: Qt.hsva(h, s, v, 1)
        function hex(col) {
            function two(x) { var t = Math.round(x * 255).toString(16); return t.length < 2 ? "0" + t : t }
            return "#" + two(col.r) + two(col.g) + two(col.b)
        }
        function edit(r, value, lbl) {
            role = r; label = lbl; original = value
            var col = Qt.lighter(value, 1.0)
            h = Math.max(0, col.hsvHue); s = col.hsvSaturation; v = col.hsvValue
            hexField.text = value
            open()
        }
        function setHex(t) {
            if (!/^#[0-9a-fA-F]{6}$/.test(t)) return
            var col = Qt.lighter(t, 1.0)
            if (col.hsvSaturation > 0) h = Math.max(0, col.hsvHue)
            s = col.hsvSaturation; v = col.hsvValue
        }
        onCurrentChanged: if (!hexField.activeFocus) hexField.text = hex(current)

        anchors.centerIn: Overlay.overlay
        width: 380; height: 400; modal: true; padding: 18
        background: Rectangle { color: ui.panel; border.color: ui.cyan; border.width: 1 }
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0.02, 0.04, 0.7) }

        ColumnLayout {
            anchors.fill: parent; spacing: 12
            RowLayout {
                Rectangle { implicitWidth: 34; implicitHeight: 20; color: ui.amber
                            Text { anchors.centerIn: parent; text: "EDIT"; font.family: ui.mono; font.pixelSize: 10; font.bold: true; color: ui.bg } }
                Head { text: picker.label.toUpperCase() }
            }
            RowLayout {
                spacing: 12
                // saturation / value square
                Rectangle {
                    id: sv
                    implicitWidth: 260; implicitHeight: 200
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "white" }
                        GradientStop { position: 1; color: Qt.hsva(picker.h, 1, 1, 1) }
                    }
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0; color: "transparent" }
                            GradientStop { position: 1; color: "black" }
                        }
                    }
                    Rectangle {
                        width: 14; height: 14; radius: 7; color: "transparent"
                        border.color: picker.v > 0.5 ? "black" : "white"; border.width: 2
                        x: picker.s * sv.width - 7; y: (1 - picker.v) * sv.height - 7
                    }
                    MouseArea {
                        anchors.fill: parent
                        function pick(m) { picker.s = Math.min(1, Math.max(0, m.x / width))
                                           picker.v = Math.min(1, Math.max(0, 1 - m.y / height)) }
                        onPressed: (m) => pick(m); onPositionChanged: (m) => pick(m)
                    }
                }
                // hue bar
                Rectangle {
                    id: hueBar
                    implicitWidth: 24; implicitHeight: 200
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#ff0000" } GradientStop { position: 0.17; color: "#ffff00" }
                        GradientStop { position: 0.33; color: "#00ff00" } GradientStop { position: 0.5; color: "#00ffff" }
                        GradientStop { position: 0.67; color: "#0000ff" } GradientStop { position: 0.83; color: "#ff00ff" }
                        GradientStop { position: 1.0; color: "#ff0000" }
                    }
                    Rectangle { width: parent.width + 6; x: -3; height: 4; y: picker.h * hueBar.height - 2
                                color: "transparent"; border.color: "white"; border.width: 2 }
                    MouseArea {
                        anchors.fill: parent
                        function pick(m) { picker.h = Math.min(0.999, Math.max(0, m.y / height)) }
                        onPressed: (m) => pick(m); onPositionChanged: (m) => pick(m)
                    }
                }
                // old / new
                ColumnLayout {
                    spacing: 0
                    Rectangle { implicitWidth: 40; implicitHeight: 100; color: picker.current }
                    Rectangle { implicitWidth: 40; implicitHeight: 100; color: picker.original
                                MouseArea { anchors.fill: parent; onClicked: picker.setHex(picker.original) } }
                }
            }
            RowLayout {
                spacing: 10
                Mono { text: "HEX"; color: ui.dim; font.pixelSize: 11 }
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: 32; color: ui.panel2
                    border.color: hexField.activeFocus ? ui.cyan : ui.line
                    TextInput {
                        id: hexField
                        anchors.fill: parent; anchors.leftMargin: 10; verticalAlignment: TextInput.AlignVCenter
                        color: ui.text; font.family: ui.mono; font.pixelSize: 14; maximumLength: 7
                        onTextEdited: picker.setHex(text)
                    }
                }
                Mono { text: "was " + picker.original; color: ui.faint; font.pixelSize: 11 }
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                NervButton { Layout.fillWidth: true; text: "CANCEL"; accent: ui.dim; onClicked: picker.close() }
                NervButton { Layout.fillWidth: true; text: "COMMIT"; solid: true
                             onClicked: { studio.setColor(picker.role, picker.hex(picker.current)); picker.close() } }
            }
        }
    }

    Popup {
        id: confirmApply
        property var items: []
        property bool undo: false          // false: apply a theme; true: restore the original configs
        readonly property bool touchesUser: items.some(function (x) { return x.user })
        anchors.centerIn: Overlay.overlay
        width: 560; modal: true; padding: 20
        background: Rectangle { color: ui.panel; border.color: confirmApply.touchesUser ? ui.amber : ui.cyan }
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0.02, 0.04, 0.7) }
        contentItem: ColumnLayout {
            spacing: 10
            RowLayout {
                Rectangle { implicitWidth: 64; implicitHeight: 20; color: ui.amber
                            Text { anchors.centerIn: parent; text: "CONFIRM"; font.family: ui.mono; font.pixelSize: 10
                                   font.bold: true; color: ui.bg } }
                Head { text: confirmApply.undo ? "RESTORE ORIGINAL CONFIGURATION" : "SYNCHRONISE " + studio.name.toUpperCase() }
            }
            Repeater {
                model: confirmApply.items
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Mono { text: modelData.user ? "!" : "·"; color: modelData.user ? ui.amber : ui.faint
                           Layout.preferredWidth: 10; font.bold: true }
                    Mono { text: modelData.text; color: modelData.user ? ui.text : ui.dim; font.pixelSize: 12
                           wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
            }
            Mono {
                visible: confirmApply.touchesUser; Layout.fillWidth: true; wrapMode: Text.Wrap
                text: confirmApply.undo
                      ? "! puts back a setting in your own config files, as it was before Theme Studio. Every theme you made stays in your themes folder."
                      : "! changes one of your own config files. A backup is made first; RESTORE ORIGINAL undoes it."
                color: ui.amber; font.pixelSize: 11
            }
            RowLayout {
                Layout.fillWidth: true; Layout.topMargin: 6; spacing: 10
                NervButton { Layout.fillWidth: true; text: "ABORT"; accent: ui.dim; onClicked: confirmApply.close() }
                NervButton { Layout.fillWidth: true; text: confirmApply.undo ? "RESTORE" : "SYNCHRONISE"; solid: true
                             accent: confirmApply.touchesUser ? ui.amber : ui.cyan
                             onClicked: { confirmApply.close()
                                          if (confirmApply.undo) studio.confirmUnhook(); else studio.confirmApply() } }
            }
        }
    }

    Shortcut { sequences: ["Ctrl+Return", "Ctrl+Enter"]; enabled: !studio.busy; onActivated: generateBtn.clicked() }
    Shortcut { sequence: "Ctrl+O"; onActivated: fileDialog.open() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: Qt.quit() }
}
