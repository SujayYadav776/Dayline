import QtQuick
import Dayline

// Bottom calendar strip (mockup): seven day columns on white with hairline
// dividers, today's number in a red circle, a gray completion fill anchored
// at the bottom of each column, and a raised tab with a chevron over the
// selected day that toggles the pull-up Progress panel.
Rectangle {
    id: strip
    objectName: "weekStrip"
    required property var vm              // App.weekVM
    property bool progressOpen: false
    signal dayPicked(string dateStr)
    signal progressToggled()

    color: Theme.surface
    height: 96

    // faint shadow where paper meets the strip
    Rectangle {
        anchors.bottom: parent.top
        width: parent.width
        height: 6
        visible: !Theme.dark
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 1.0; color: "#14000000" }
        }
    }

    // ---- selected column index (tab anchor) ------------------------------
    readonly property int cellCount: vm ? vm.strip.length : 0
    function idxOf(flag) {
        if (!vm) return -1
        for (var i = 0; i < vm.strip.length; i++)
            if (vm.strip[i][flag]) return i
        return -1
    }
    readonly property int selectedIdx: {
        var i = idxOf("isSelected")
        if (i < 0) i = idxOf("isToday")
        return i < 0 ? Math.floor(cellCount / 2) : i
    }
    readonly property real colW: cellCount > 0 ? width / 7 : width

    // ---- day columns ------------------------------------------------------
    Row {
        anchors.fill: parent
        Repeater {
            id: cells
            model: strip.vm ? strip.vm.strip : []
            delegate: Rectangle {
                id: cell
                required property var modelData
                width: strip.colW
                height: strip.height
                color: "transparent"

                // hairline divider between columns
                Rectangle {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 1
                    color: Theme.border
                }

                // completion fill anchored at the bottom (mockup: gray block)
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: (parent.height - 44) * (modelData.percent / 100)
                    color: Theme.stripFill
                    visible: height > 0.5
                    Behavior on height { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs } }
                }

                Row {
                    id: head
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 12
                    spacing: 10

                    // number — red circle when today
                    Rectangle {
                        id: numBox
                        width: modelData.isToday ? 30 : numText.implicitWidth
                        height: modelData.isToday ? 30 : numText.implicitHeight
                        radius: 15
                        color: modelData.isToday ? Theme.accent : "transparent"
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            id: numText
                            anchors.centerIn: parent
                            text: modelData.dayNum
                            color: modelData.isToday ? Theme.accentInk
                                 : modelData.isFuture ? Theme.prioNone : Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 17
                            font.weight: Theme.weightLabel
                        }
                    }
                    Text {
                        text: modelData.letter
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 15
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: strip.dayPicked(modelData.dateStr)
                }
                Accessible.role: Accessible.Button
                Accessible.name: modelData.dateStr + (modelData.isToday ? ", today" : "")
            }
        }
    }

    // ---- raised tab over the selected column (toggles Progress) ----------
    Item {
        id: tabZone
        objectName: "progressTab"
        width: 96
        height: 26
        anchors.bottom: parent.top
        x: Math.max(2, Math.min(strip.width - width - 2,
                                strip.colW * strip.selectedIdx + strip.colW / 2 - width / 2))

        Rectangle {
            anchors.fill: parent
            anchors.bottomMargin: -8          // merge into the strip body
            radius: 12
            color: Theme.surface
        }
        // squared bottom corners overlapping the strip
        Rectangle {
            x: 0
            y: parent.height - 12
            width: parent.width
            height: 12
            color: Theme.surface
        }
        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -1
            text: strip.progressOpen ? "⌄" : "⌃"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: 14
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: strip.progressToggled()
        }
        Accessible.role: Accessible.Button
        Accessible.name: strip.progressOpen ? "Close progress" : "Open progress"
    }
}
