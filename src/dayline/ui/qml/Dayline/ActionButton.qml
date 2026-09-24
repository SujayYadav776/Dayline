import QtQuick

// shadcn/ui-style button. `variant`: default(primary) | secondary | outline | ghost.
// font-medium, h-9, rounded-md, hover/press states, focus ring (ring-2 ring-offset).
Rectangle {
    id: btn
    required property string text
    property string variant: "outline"
    signal clicked()
    property bool pressed: mouse.pressed
    property bool enabled: true

    readonly property bool primary: variant === "default"
    readonly property bool plain: variant === "ghost" || variant === "outline"

    implicitWidth: Math.max(label.implicitWidth + 2 * Theme.s16, 40)
    implicitHeight: 36
    width: implicitWidth
    height: implicitHeight
    radius: Theme.radiusControl
    opacity: enabled ? 1.0 : 0.5

    color: !enabled ? Theme.surfaceAlt
         : primary ? (pressed ? Theme.accentHover : Theme.accent)
         : variant === "secondary" ? (mouse.containsMouse ? Theme.border : Theme.surfaceAlt)
         : variant === "ghost" ? (mouse.containsMouse ? Theme.surfaceAlt : "transparent")
         : (mouse.containsMouse ? Theme.surfaceAlt : Theme.surface)   // outline
    border.color: plain ? Theme.input : "transparent"
    border.width: variant === "outline" ? 1 : 0

    // focus ring (ring-2, offset 2)
    Rectangle {
        anchors.fill: parent
        anchors.margins: -(Theme.ringWidth + Theme.ringOffset)
        radius: btn.radius + Theme.ringWidth + Theme.ringOffset
        color: "transparent"
        border.color: Theme.ring
        border.width: mouse.activeFocus ? Theme.ringWidth : 0
        Behavior on border.width { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs } }
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: btn.text
        color: !btn.enabled ? Theme.textSecondary : btn.primary ? Theme.accentInk : Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
        font.weight: Theme.weightLabel
        font.letterSpacing: Theme.headingTracking
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        focus: true
        acceptedButtons: Qt.LeftButton
        cursorShape: btn.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (btn.enabled) btn.clicked()
    }
    Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }

    Accessible.role: Accessible.Button
    Accessible.name: btn.text
    Accessible.onPressAction: if (btn.enabled) btn.clicked()
}
