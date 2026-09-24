import QtQuick
import QtQuick.Controls
import Dayline

// Pull-up "Progress" panel (second mockup screen): slides over the page with
// the paper background, a typewriter-serif title stack, the "My week" card
// (week row + the selected day's tasks), "Day streak" / "Tasks done" cards,
// and the "Activity" heat-map card with month labels.
Item {
    id: panel
    objectName: "progressPanel"
    required property var vm         // App.weekVM
    required property var today      // App.todayVM
    property bool open: false
    clip: true

    readonly property real cellSize: Math.min(22,
        (width - 2 * Theme.s16 - 2 * Theme.s16 - 12 * 6) / 13)

    // block interaction with the page below while open
    MouseArea {
        anchors.fill: parent
        enabled: panel.open
        hoverEnabled: true
    }

    Rectangle {
        id: sheet
        objectName: "progressSheet"
        width: parent.width
        height: parent.height
        color: Theme.bg
        y: panel.open ? 0 : panel.height + 40
        Behavior on y {
            enabled: Theme.animate
            NumberAnimation { duration: Theme.panelMotionMs; easing.type: Easing.OutCubic }
        }
        Image {
            anchors.fill: parent
            source: "../../assets/paper.png"
            fillMode: Image.Tile
            opacity: Theme.dark ? 0.05 : 0.55
        }
        // top hairline + soft shadow so the sheet reads as a raised layer
        Rectangle {
            anchors.bottom: parent.top
            width: parent.width
            height: 8
            visible: !Theme.dark
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#00000000" }
                GradientStop { position: 1.0; color: "#1A000000" }
            }
        }

        Flickable {
            anchors.fill: parent
            contentHeight: col.implicitHeight + Theme.s32
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            visible: panel.open

            Column {
                id: col
                x: Theme.s24
                width: parent.width - 2 * Theme.s24
                spacing: Theme.s24

                // ---- title -------------------------------------------------
                Text {
                    topPadding: Theme.s16
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Progress"
                    font.family: Theme.serifFamily
                    font.pixelSize: 26
                    font.weight: Theme.weightHeading
                    color: Theme.text
                }

                // ---- My week ------------------------------------------------
                Item {
                    width: parent.width
                    height: 30
                    Text {
                        anchors.centerIn: parent
                        text: "My week"
                        font.family: Theme.serifFamily
                        font.pixelSize: 20
                        font.weight: Theme.weightHeading
                        color: Theme.text
                    }
                    // share glyph (mockup, top-right of the section)
                    Image {
                        id: shareIcon
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        source: "../../assets/share.png"
                        smooth: true
                    }
                }

                Rectangle {
                    id: weekCard
                    width: parent.width
                    height: Theme.s16 + stripRow.height + Theme.s12
                            + Math.min(tasksFlick.contentHeight, 220) + Theme.s16
                    radius: Theme.radiusCard
                    color: Theme.surface

                    Column {
                        id: weekCol
                        x: Theme.s16
                        y: Theme.s16
                        width: parent.width - 2 * Theme.s16
                        spacing: Theme.s12

                        // week row: numbers + letters, today in a red circle
                        Row {
                            id: stripRow
                            width: parent.width
                            height: 30
                            Repeater {
                                model: panel.vm ? panel.vm.strip : []
                                delegate: Item {
                                    required property var modelData
                                    required property int index
                                    width: parent.width / 7
                                    height: 30
                                    Row {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        spacing: 8
                                        Rectangle {
                                            width: modelData.isToday ? 28 : numT.implicitWidth
                                            height: width
                                            radius: width / 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: modelData.isToday ? Theme.accent : "transparent"
                                            Text {
                                                id: numT
                                                anchors.centerIn: parent
                                                text: modelData.dayNum
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 15
                                                font.weight: Theme.weightLabel
                                                color: modelData.isToday ? Theme.accentInk : Theme.text
                                            }
                                        }
                                        Text {
                                            text: modelData.letter
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 13
                                            color: Theme.textSecondary
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                }
                            }
                        }

                        // selected day's tasks (completed inline, ticked + struck)
                        Flickable {
                            id: tasksFlick
                            width: parent.width
                            height: Math.min(contentHeight, 220)
                            contentHeight: tasksCol.implicitHeight
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: tasksCol
                                width: parent.width
                                spacing: Theme.s12

                                Repeater {
                                    model: panel.today ? panel.today.tasksList : []
                                    delegate: Row {
                                        required property var modelData
                                        width: tasksCol.width
                                        spacing: Theme.s12
                                        Rectangle {
                                            width: 14
                                            height: 14
                                            radius: 7
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: modelData.statusKind === "done" ? Theme.accent : "transparent"
                                            border.color: modelData.statusKind === "done"
                                                          ? Theme.accent : Theme.input
                                            border.width: 1.5
                                            Text {
                                                anchors.centerIn: parent
                                                visible: modelData.statusKind === "done"
                                                text: "✓"
                                                font.pixelSize: 9
                                                font.weight: Font.Bold
                                                color: Theme.accentInk
                                            }
                                        }
                                        Text {
                                            width: parent.width - 14 - parent.spacing
                                            text: modelData.description
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 13
                                            color: modelData.statusKind === "done" ? Theme.textSecondary : Theme.text
                                            font.strikeout: modelData.statusKind === "done"
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                                Text {
                                    visible: !panel.today || panel.today.tasksList.length === 0
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "No tasks on this day."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }
                }

                // ---- streak / done cards ------------------------------------
                Row {
                    width: parent.width
                    spacing: Theme.s16
                    Repeater {
                        model: [
                            {"emoji": "🐟", "count": panel.vm ? panel.vm.streak : 0,
                             "label": "Day streak"},
                            {"emoji": "⭐", "count": panel.vm ? panel.vm.doneToday : 0,
                             "label": "Tasks done"}
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            width: (panel.width - 2 * Theme.s24 - Theme.s16) / 2
                            height: 104
                            radius: Theme.radiusCard
                            color: Theme.surface
                            Row {
                                anchors.fill: parent
                                anchors.margins: Theme.s16
                                spacing: Theme.s12
                                Text {
                                    text: modelData.emoji
                                    font.pixelSize: 34
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Column {
                                    width: parent.width - 34 - Theme.s12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2
                                    Text {
                                        text: modelData.count + " ✦"
                                        font.family: Theme.serifFamily + ", Segoe UI Symbol"
                                        font.pixelSize: 16
                                        font.weight: Theme.weightHeading
                                        color: Theme.text
                                    }
                                    Text {
                                        text: modelData.label
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 15
                                        font.weight: Theme.weightHeading
                                        color: Theme.text
                                    }
                                }
                            }
                        }
                    }
                }

                // ---- Activity heat-map --------------------------------------
                Rectangle {
                    width: parent.width
                    height: actCol.implicitHeight + 2 * Theme.s24
                    radius: Theme.radiusCard
                    color: Theme.surface

                    Column {
                        id: actCol
                        x: Theme.s24
                        y: Theme.s24
                        width: parent.width - 2 * Theme.s24
                        spacing: Theme.s16

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Activity"
                            font.family: Theme.serifFamily
                            font.pixelSize: 20
                            font.weight: Theme.weightHeading
                            color: Theme.text
                        }

                        // month labels aligned above their week columns
                        Item {
                            width: parent.width
                            height: 20
                            Repeater {
                                model: panel.vm ? panel.vm.activityMonths : []
                                delegate: Text {
                                    required property var modelData
                                    x: modelData.col * (panel.cellSize + 6)
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.label
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 15
                                    color: Theme.text
                                }
                            }
                        }

                        Grid {
                            rows: 7
                            flow: Grid.LayoutDown
                            columnSpacing: 6
                            rowSpacing: 6
                            Repeater {
                                model: panel.vm ? panel.vm.activity : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: panel.cellSize
                                    height: panel.cellSize
                                    radius: 4
                                    color: modelData.future ? "transparent"
                                             : Theme.heatColor(modelData.level)
                                }
                            }
                        }
                    }
                }

                Item { width: 1; height: Theme.s16 }
            }
        }
    }

    Accessible.name: "Progress panel"
    Accessible.role: Accessible.Pane
}
