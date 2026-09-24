import QtQuick

// shadcn/ui switch: pill track (primary when on, input/border off), white thumb.
// Drop-in for Controls.Switch — expose `checked` + `toggled` (checked is bound to
// the VM; a click only emits toggled() and the VM round-trips the value back).
Item {
    id: ctl
    property bool checked: false
    signal toggled()

    implicitWidth: 40
    implicitHeight: 22
    width: implicitWidth
    height: implicitHeight
    Accessible.role: Accessible.CheckBox
    Accessible.name: parent ? parent.Accessible.name : ""
    Accessible.checked: ctl.checked

    Rectangle {
        anchors.fill: parent
        radius: parent.height / 2
        color: ctl.checked ? Theme.accent : "transparent"
        border.color: ctl.checked ? Theme.accent : Theme.input
        border.width: 1
        opacity: mouse.enabled ? 1 : 0.5
        Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
    }
    Rectangle {
        id: thumb
        width: parent.height - 4
        height: width
        radius: width / 2
        anchors.verticalCenter: parent.verticalCenter
        x: ctl.checked ? parent.width - width - 2 : 2
        color: Theme.bg
        border.color: ctl.checked ? "transparent" : Theme.border
        border.width: ctl.checked ? 0 : 1
        Behavior on x { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs; easing.type: Easing.OutCubic } }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: ctl.toggled()
    }
}
