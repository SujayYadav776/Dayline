import QtQuick
import QtQuick.Controls

// Staggered menu — QML port of the React Bits <StaggeredMenu /> (D-033),
// matched to the real GSAP source + CSS:
//   • two pre-layers sweep in first as colour bands — the app's heat-map
//     ramp (salmon → bookmark red) — 380ms power4.out, 50ms stagger
//   • the paper panel trails them (460ms power4.out, +160ms)
//   • uppercase labels rise out of clipped rows with a 10° tilt
//     (600ms power4.out, 60ms stagger, starting ~200ms in)
//   • superscript numbers fade in just behind each label
//   • closing is one synchronized 240ms power3.in exit; labels hold still
//     and reset only once the panel is offscreen
//   • ≤1024px the panel is full width (media query in the original CSS) —
//     the widget is always that small, so the panel fills the window
//
// Direction-aware Behaviors were tried first, but the timing bindings inside
// a Behavior still read the OLD value when the trigger fires — the exit ran
// with entrance timings. Every slider therefore uses explicit open/close
// animations started from an on<sync>Changed handler instead.
//
// The bookmark ribbon in Main.qml replaces the component's built-in
// Menu/Close toggle (and floats above the panel, like the original header
// sits above it); the socials block has no Dayline equivalent and is
// dropped. The component NEVER assigns `opened`: the host owns the flag
// (win.drawerOpen), outside clicks emit dismiss(), rows emit itemChosen().
Item {
    id: root

    property bool opened: false            // bind from the host
    property var items: []                 // [{id, label}]
    // pre-layer stack: two bands from the app's heat-map ramp (salmon leads,
    // bookmark red trails against the panel)
    readonly property var layerColors: [
        Theme.heatColor(2), Theme.heatColor(4)
    ]

    signal dismiss()
    signal itemChosen(string id)

    readonly property real offscreenX: -width   // slides in from the ribbon side
    // stay alive through the closing slide, then drop out (also clears UIA)
    visible: root.opened || panel.exiting

    // click-away (the original listens for document mousedown outside panel+toggle)
    MouseArea {
        anchors.fill: parent
        enabled: root.opened
        onClicked: root.dismiss()
    }

    // ---- staggered pre-layers ------------------------------------------------
    Repeater {
        id: layerRep
        objectName: "layerRep"
        model: root.layerColors
        delegate: Rectangle {
            id: layer
            objectName: "menuLayer"
            required property int index
            required property var modelData
            width: root.width
            height: root.height
            x: root.offscreenX
            color: modelData
            visible: root.opened || panel.exiting
            z: 5

            SequentialAnimation {
                id: openAnim
                PauseAnimation { duration: layer.index * 50 }
                NumberAnimation {
                    target: layer
                    property: "x"
                    to: 0
                    duration: 380
                    easing.type: Easing.OutQuart
                }
            }
            NumberAnimation {
                id: closeAnim
                target: layer
                property: "x"
                to: root.offscreenX
                duration: 240
                easing.type: Easing.InCubic
            }
            property bool sync: root.opened
            onSyncChanged: {
                if (!Theme.animate) {
                    layer.x = sync ? 0 : root.offscreenX
                    return
                }
                if (sync) {
                    closeAnim.stop()
                    openAnim.restart()
                } else {
                    openAnim.stop()
                    closeAnim.restart()
                }
            }
        }
    }

    // ---- paper panel -----------------------------------------------------------
    Rectangle {
        id: panel
        objectName: "menuPanel"
        width: root.width
        height: root.height
        x: root.offscreenX
        color: Theme.surface
        z: 10
        property bool exiting: closeAnim.running

        SequentialAnimation {
            id: openAnim
            PauseAnimation { duration: root.layerColors.length * 50 + 60 }
            NumberAnimation {
                target: panel
                property: "x"
                to: 0
                duration: 460
                easing.type: Easing.OutQuart
            }
        }
        NumberAnimation {
            id: closeAnim
            target: panel
            property: "x"
            to: root.offscreenX
            duration: 240
            easing.type: Easing.InCubic
        }
        property bool sync: root.opened
        onSyncChanged: {
            if (!Theme.animate) {
                panel.x = sync ? 0 : root.offscreenX
                return
            }
            if (sync) {
                closeAnim.stop()
                openAnim.restart()
            } else {
                openAnim.stop()
                closeAnim.restart()
            }
        }

        Image {
            anchors.fill: parent
            source: "../assets/paper.png"
            fillMode: Image.Tile
            opacity: Theme.dark ? 0.05 : 0.35
        }
        // swallow clicks inside the panel so they don't hit the click-away layer
        MouseArea { anchors.fill: parent; onClicked: mouse.accepted = true }
        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.border
        }

        // ---- numbered items ------------------------------------------------------
        // y 124 clears the bookmark ribbon, which hangs over the top-left corner
        // of the panel exactly like it does over every other page.
        Column {
            id: itemsCol
            x: Theme.s24
            y: 124
            width: panel.width - 2 * Theme.s24
            spacing: 8

            Repeater {
                model: root.items
                delegate: Rectangle {
                    id: navRow
                    required property int index
                    required property var modelData
                    width: itemsCol.width
                    height: 46
                    color: "transparent"
                    clip: true                       // .sm-panel-itemWrap overflow:hidden

                    // 0 = tucked below the clip line, 1 = seated
                    property real pos: 0

                    SequentialAnimation {
                        id: enterAnim
                        // starts 15% into the panel slide, then 100ms per row
                        PauseAnimation { duration: 200 + navRow.index * 60 }
                        NumberAnimation {
                            target: navRow
                            property: "pos"
                            to: 1
                            duration: 600
                            easing.type: Easing.OutQuart
                        }
                    }
                    // hold labels still while the panel exits, reset once gone
                    Timer {
                        id: resetTimer
                        interval: 260
                        onTriggered: if (!root.opened) navRow.pos = 0
                    }
                    property bool sync: root.opened
                    onSyncChanged: {
                        if (!Theme.animate) {
                            resetTimer.stop()
                            navRow.pos = sync ? 1 : 0
                            return
                        }
                        if (sync) {
                            resetTimer.stop()
                            enterAnim.restart()
                        } else {
                            enterAnim.stop()
                            resetTimer.restart()
                        }
                    }

                    Text {
                        id: label
                        anchors.verticalCenter: parent.verticalCenter
                        text: String(navRow.modelData.label || "").toUpperCase()
                        font.family: Theme.menuFamily
                        font.pixelSize: 32
                        font.letterSpacing: 0.5
                        color: hover.hovered ? Theme.accent : Theme.text
                        Behavior on color {
                            enabled: Theme.animate
                            ColorAnimation { duration: 250; easing.type: Easing.OutQuad }
                        }
                        transform: [
                            Rotation {
                                origin.x: label.width / 2
                                origin.y: label.height
                                angle: (1 - navRow.pos) * 10
                            },
                            Translate { y: (1 - navRow.pos) * label.height * 1.4 }
                        ]
                    }
                    Text {
                        // decimal-leading-zero superscript, fading in behind the label
                        text: String(navRow.index + 1).padStart(2, "0")
                        color: Theme.accent
                        font.family: Theme.serifFamily
                        font.pixelSize: 13
                        opacity: Math.max(0, Math.min(1, (navRow.pos - 0.3) / 0.45))
                        anchors {
                            left: label.right
                            leftMargin: 6
                            top: label.top
                            topMargin: 4
                        }
                    }
                    HoverHandler { id: hover }
                    TapHandler {
                        onTapped: {
                            root.itemChosen(String(navRow.modelData.id || ""))
                            root.dismiss()
                        }
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: navRow.modelData.label || ""
                }
            }
        }
    }
}
