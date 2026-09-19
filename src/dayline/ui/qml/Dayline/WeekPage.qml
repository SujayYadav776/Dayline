import QtQuick
import QtQuick.Controls
import Dayline

// Week overview (FR-W1/W2): ‹ › nav, seven day rows, week total, heat-map.
Item {
    id: page
    required property var vm      // App.weekVM

    Column {
        anchors.fill: parent
        anchors.leftMargin: Theme.s24
        anchors.rightMargin: Theme.s24
        spacing: Theme.s16

        // ---- header --------------------------------------------------------
        Item {
            width: parent.width
            height: 40
            Row {
                id: nav
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.s8
                Repeater {
                    model: ["‹", "›"]
                    delegate: Rectangle {
                        width: 32; height: 32
                        radius: Theme.radiusControl
                        color: Theme.surface
                        border.color: Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 16
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: modelData === "‹" ? page.vm.prevWeek() : page.vm.nextWeek()
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData === "‹" ? "Previous week" : "Next week"
                    }
                }
            }
            Text {
                anchors.left: nav.right
                anchors.leftMargin: Theme.s12
                anchors.verticalCenter: parent.verticalCenter
                text: page.vm.rangeLabel
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: tt.implicitWidth + Theme.s16
                height: 24
                radius: Theme.radiusChip
                color: Theme.surfaceAlt
                border.color: Theme.border
                Text {
                    id: tt
                    anchors.centerIn: parent
                    text: "This week"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: page.vm.thisWeek()
                }
            }
        }

        // ---- week total card -----------------------------------------------
        Rectangle {
            width: parent.width
            height: 72
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            Row {
                anchors.fill: parent
                anchors.margins: Theme.s16
                spacing: Theme.s16
                ProgressRing {
                    width: 44; height: 44
                    anchors.verticalCenter: parent.verticalCenter
                    lineWidth: 5
                    value: page.vm.weekTotal > 0 ? page.vm.weekDone / page.vm.weekTotal : 0
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.s4
                    Text {
                        text: page.vm.weekDone + " of " + page.vm.weekTotal + " done this week"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sectionPx
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: page.vm.weekPercent + "% complete"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                    }
                }
            }
        }

        // ---- day rows ------------------------------------------------------
        Column {
            width: parent.width
            spacing: Theme.s8
            Repeater {
                model: page.vm.days
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 40
                    radius: Theme.radiusControl
                    color: modelData.isToday ? Theme.surfaceAlt : "transparent"
                    border.color: modelData.isToday ? Theme.accent : "transparent"
                    border.width: modelData.isToday ? 1 : 0
                    opacity: modelData.isFuture ? 0.6 : 1.0
                    Row {
                        anchors.fill: parent
                        anchors.margins: Theme.s12
                        spacing: Theme.s12
                        Text {
                            width: 52
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label + " " + modelData.dayNum
                            color: modelData.isToday ? Theme.accent : Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.bodyPx
                            font.weight: modelData.isToday ? Font.DemiBold : Font.Normal
                        }
                        Rectangle {
                            width: parent.width - 52 - countText.width - 2 * parent.spacing
                            height: 8
                            radius: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.surfaceAlt
                            Rectangle {
                                width: parent.width * (modelData.total > 0 ? modelData.percent / 100 : 0)
                                height: parent.height
                                radius: parent.radius
                                color: modelData.total > 0 && modelData.percent === 100
                                       ? Theme.success : Theme.accent
                                Behavior on width { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs } }
                            }
                        }
                        Text {
                            id: countText
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.total > 0 ? modelData.done + "/" + modelData.total : "—"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.captionPx
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: page.vm.openDay(modelData.dateStr)
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.label + ": " + modelData.done + " of " + modelData.total
                }
            }
        }
    }

    Accessible.name: "Week overview"
    Accessible.role: Accessible.Pane
}
