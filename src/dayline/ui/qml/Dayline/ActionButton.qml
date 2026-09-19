import QtQuick

// Secondary action button (surface style) for settings actions.
Rectangle {
    id: btn
    required property string text
    signal clicked()
    property bool hovered: mouse.containsMouse
    property bool pressed: mouse.pressed

    width: label.implicitWidth + 2 * Theme.s16
    height: 34
    radius: Theme.radiusControl
    color: pressed ? Theme.surfaceAlt : (hovered ? Theme.surfaceAlt : Theme.surface)
    border.color: Theme.border
    border.width: 1
    Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }

    Text {
        id: label
        anchors.centerIn: parent
        text: btn.text
        color: Theme.accent
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: btn.clicked()
    }
    Accessible.role: Accessible.Button
    Accessible.name: btn.text
}
