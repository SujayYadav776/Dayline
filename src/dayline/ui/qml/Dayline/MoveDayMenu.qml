import QtQuick
import Dayline

// Reschedule card (replaces the old drag-to-reschedule gesture): seven day
// chips from the bottom strip — pick one and the task moves there through the
// already-tested App.rescheduleTask path (line moved, 📅 rewritten, single
// undoable step). Opened via win.openMoveMenu(); closes on chip, ✕, Esc or
// any click on the backdrop behind it.
Rectangle {
    id: menu
    objectName: "moveDayMenu"

    property int taskKey: -1
    property string taskText: ""
    property var strip: []              // vm.weekVM.strip rows

    color: Theme.surface
    border.color: Theme.border
    border.width: 1
    radius: Theme.radiusCard
    opacity: 0
    visible: opacity > 0.01
    Behavior on opacity {
        enabled: Theme.animate
        NumberAnimation { duration: Theme.motionMs; easing.type: Easing.OutCubic }
    }

    function open(key, text, stripModel) {
        menu.taskKey = key
        menu.taskText = text
        menu.strip = stripModel || []
        menu.opacity = 1
        menu.forceActiveFocus()
    }
    function close() {
        menu.opacity = 0
        menu.taskKey = -1
    }
    Keys.onEscapePressed: menu.close()

    Column {
        id: col
        x: Theme.s16
        y: Theme.s12
        width: parent.width - 2 * Theme.s16
        spacing: Theme.s10

        Row {
            width: parent.width
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Move to day"
                color: Theme.text
                font.family: Theme.serifFamily
                font.pixelSize: Theme.labelPx
                font.weight: Font.Bold
            }
            Item { width: parent.width - moveHead.implicitWidth - closeBox.width; height: 1 }
            Rectangle {
                id: closeBox
                anchors.verticalCenter: parent.verticalCenter
                width: 24; height: 24; radius: 12
                color: closeMouse.pressed ? Theme.surfaceAlt : "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "✕"; color: Theme.textSecondary
                    font.family: Theme.fontFamily; font.pixelSize: 13
                }
                MouseArea {
                    id: closeMouse
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: menu.close()
                }
            }
        }

        Text {
            id: moveHead
            width: parent.width
            text: menu.taskText
            elide: Text.ElideRight
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.captionPx
        }

        Row {
            width: parent.width
            spacing: 6
            Repeater {
                model: menu.strip
                delegate: Rectangle {
                    id: chip
                    required property var modelData
                    readonly property bool isCurrent: !!modelData.isSelected
                    width: (col.width - 6 * 6) / 7
                    height: chipCol.height + 14
                    radius: Theme.radiusControl
                    color: mouse.pressed && !isCurrent ? Theme.surfaceAlt : "transparent"
                    border.color: modelData.isToday ? Theme.accent : Theme.border
                    border.width: modelData.isToday ? 2 : 1
                    opacity: isCurrent ? 0.35 : 1.0

                    Column {
                        id: chipCol
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.letter
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.dayNum
                            color: modelData.isToday ? Theme.accent : Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 15
                            font.weight: Theme.weightLabel
                        }
                    }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        enabled: !chip.isCurrent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            App.rescheduleTask(menu.taskKey, modelData.dateStr)
                            menu.close()
                        }
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: "Move to " + modelData.dateStr
                }
            }
        }
    }

    height: col.y + col.height + Theme.s12
}
