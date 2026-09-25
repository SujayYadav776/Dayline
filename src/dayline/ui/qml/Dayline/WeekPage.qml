import QtQuick
import QtQuick.Controls
import Dayline

// Week overview (FR-W1/W2/W3), restyled with the shadcn/ui design language
// (D-039): dashboard cards (muted eyebrow → headline number), a bordered
// table for the day rows (uppercase micro-headers, hairline separators,
// hover wash), ghost icon buttons, thin progress tracks, and a heat legend.
// shadcn's own CLI can't target QML, so this is a faithful port of its
// component grammar onto the Dayline paper tokens — structure, restraint,
// 4 px rhythm, one accent — not a new palette.
Item {
    id: page
    required property var vm      // App.weekVM

    // shadcn table column model (row height / hairlines shared by header+rows)
    readonly property int rowH: 44
    readonly property int labelW: 76
    readonly property int countW: 46

    Flickable {
        anchors.fill: parent
        anchors.topMargin: Theme.ribbonOverhang
        anchors.leftMargin: Theme.s24
        anchors.rightMargin: Theme.s24
        contentWidth: width
        contentHeight: pageCol.height
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: pageCol
            width: parent.width
            spacing: Theme.s16

        // ---- header: ghost nav + range + outline "This week" button ---------
        Item {
            width: parent.width
            height: 36
            Row {
                id: nav
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.s4
                Repeater {
                    model: ["‹", "›"]
                    delegate: Rectangle {
                        width: 32; height: 32
                        radius: Theme.radiusControl
                        // shadcn ghost button: transparent until hovered
                        color: wnavBtn.containsMouse ? Theme.surfaceAlt : "transparent"
                        Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 16
                        }
                        MouseArea {
                            id: wnavBtn
                            anchors.fill: parent
                            hoverEnabled: true
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
                anchors.leftMargin: Theme.s8
                anchors.right: twBtnWrap.left
                anchors.rightMargin: Theme.s8
                anchors.verticalCenter: parent.verticalCenter
                text: page.vm.rangeLabel
                font.family: Theme.serifFamily
                font.pixelSize: Theme.sectionPx
                font.weight: Theme.weightHeading
                color: Theme.text
                elide: Text.ElideRight
            }
            Rectangle {
                id: twBtnWrap
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: tt.implicitWidth + Theme.s16
                height: 28
                radius: Theme.radiusControl
                color: twBtn.containsMouse ? Theme.surfaceAlt : "transparent"
                border.color: Theme.input
                border.width: 1
                Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
                Text {
                    id: tt
                    anchors.centerIn: parent
                    text: "This week"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                    font.weight: Theme.weightLabel
                }
                MouseArea {
                    id: twBtn
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: page.vm.thisWeek()
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Jump to this week"
            }
        }

        // ---- summary card: eyebrow → headline (shadcn dashboard stat) -------
        Rectangle {
            width: parent.width
            height: sumCol.height + 1 + Theme.s12 + ringRow.height + Theme.s16
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            Column {
                id: sumCol
                x: Theme.s16
                width: parent.width - 2 * Theme.s16
                topPadding: Theme.s16
                spacing: Theme.s4
                Text {
                    text: "COMPLETION"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Theme.weightLabel
                    font.letterSpacing: 1.2
                }
                Text {
                    text: page.vm.weekPercent + "%"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 28
                    font.weight: Theme.weightHeading
                }
                Text {
                    text: page.vm.weekDone + " of " + page.vm.weekTotal + " tasks done this week"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
            }
            // CardHeader/CardContent hairline
            Rectangle {
                id: sumHr
                anchors.top: sumCol.bottom
                anchors.topMargin: Theme.s12
                width: parent.width
                height: 1
                color: Theme.border
            }
            Row {
                id: ringRow
                anchors.top: sumHr.bottom
                anchors.topMargin: Theme.s12
                anchors.left: parent.left
                anchors.leftMargin: Theme.s16
                spacing: Theme.s12
                ProgressRing {
                    width: 44; height: 44
                    anchors.verticalCenter: parent.verticalCenter
                    lineWidth: 5
                    showValue: false
                    value: page.vm.weekTotal > 0 ? page.vm.weekDone / page.vm.weekTotal : 0
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: page.vm.weekTotal === 0
                          ? "Nothing scheduled yet"
                          : page.vm.weekDone === page.vm.weekTotal
                            ? "Week complete — every box ticked"
                            : (page.vm.weekTotal - page.vm.weekDone) + " still open"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                }
            }
        }

        // ---- day table (shadcn Table inside a Card) --------------------------
        Rectangle {
            width: parent.width
            height: tableCol.height + 2 * Theme.s12
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            Column {
                id: tableCol
                x: Theme.s12
                width: parent.width - 2 * Theme.s12
                y: Theme.s12
                spacing: 0

                // micro-header row
                Item {
                    width: parent.width
                    height: 28
                    Text {
                        id: thDay
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.s4
                        anchors.verticalCenter: parent.verticalCenter
                        text: "DAY"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Theme.weightLabel
                        font.letterSpacing: 1.2
                    }
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.s4 + page.labelW + Theme.s12
                        anchors.verticalCenter: parent.verticalCenter
                        text: "PROGRESS"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Theme.weightLabel
                        font.letterSpacing: 1.2
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.s4
                        anchors.verticalCenter: parent.verticalCenter
                        text: "DONE"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Theme.weightLabel
                        font.letterSpacing: 1.2
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }

                Repeater {
                    model: page.vm.days
                    delegate: Item {
                        required property var modelData
                        required property int index
                        width: tableCol.width
                        height: page.rowH

                        Rectangle {
                            anchors.fill: parent
                            // hover wash + today selection tint (shadcn row states)
                            visible: rowMa.containsMouse || modelData.isToday
                            color: modelData.isToday ? Theme.surfaceAlt
                                 : Qt.alpha(Theme.surfaceAlt, 0.6)
                        }
                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s4
                            anchors.verticalCenter: parent.verticalCenter
                            width: page.labelW - 18
                            text: modelData.label + " " + modelData.dayNum
                            color: modelData.isToday ? Theme.accent : Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.bodyPx
                            font.weight: modelData.isToday ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                        }
                        // today marker dot
                        Rectangle {
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s4
                            anchors.top: parent.top
                            anchors.topMargin: 8
                            width: 5; height: 5; radius: 2.5
                            visible: modelData.isToday
                            color: Theme.accent
                        }
                        // thin progress track
                        Rectangle {
                            id: track
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s4 + page.labelW + Theme.s12
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - (Theme.s4 + page.labelW + Theme.s12)
                                   - page.countW - Theme.s12 - 2 * Theme.s4
                            height: 6
                            radius: 3
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
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.s4
                            anchors.verticalCenter: parent.verticalCenter
                            width: page.countW
                            horizontalAlignment: Text.AlignRight
                            text: modelData.total > 0 ? modelData.done + "/" + modelData.total : "—"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.captionPx
                        }
                        // hairline separator (last row skips — the card edge is the border)
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            visible: index < page.vm.days.length - 1
                            color: Theme.border
                        }
                        opacity: modelData.isFuture ? 0.55 : 1.0
                        MouseArea {
                            id: rowMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: page.vm.openDay(modelData.dateStr)
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.label + ": " + modelData.done + " of " + modelData.total
                    }
                }
            }
        }

        // ---- month heat-map card (FR-W3) with legend -------------------------
        Rectangle {
            width: parent.width
            height: heatCol.height + 2 * Theme.s16
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
            Column {
                id: heatCol
                x: Theme.s16
                width: parent.width - 2 * Theme.s16
                y: Theme.s16
                spacing: Theme.s12
                Item {
                    width: parent.width
                    height: 22
                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: "This month"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sectionPx
                        font.weight: Font.DemiBold
                    }
                    // legend: Less ▫▫▫▫▫ More
                    Row {
                        id: heatLegend
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.s4
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Less"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                        Repeater {
                            model: [0, 1, 2, 3, 4]
                            delegate: Rectangle {
                                width: 10; height: 10; radius: 3
                                anchors.verticalCenter: parent.verticalCenter
                                color: index === 0 ? Theme.surfaceAlt : Theme.heatColor(index)
                            }
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "More"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                    }
                }
                Grid {
                    id: heat
                    width: parent.width
                    columns: 7
                    spacing: Theme.s4
                    Repeater {
                        model: page.vm.monthHeat
                        delegate: Rectangle {
                            required property var modelData
                            width: (heat.width - 6 * heat.spacing) / 7
                            height: width
                            radius: 6
                            visible: !modelData.empty
                            color: modelData.hasTasks
                                   ? Qt.alpha(Theme.accent, 0.15 + 0.85 * modelData.percent / 100)
                                   : Theme.surfaceAlt
                            border.color: modelData.isToday ? Theme.accent : "transparent"
                            border.width: modelData.isToday ? 2 : 0
                            Text {
                                anchors.centerIn: parent
                                text: modelData.day
                                color: modelData.percent > 55 ? Theme.accentInk : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.captionPx
                            }
                            ToolTip.visible: hh.containsMouse
                            ToolTip.text: modelData.dateStr + " · " + modelData.percent + "%"
                            HoverHandler { id: hh }
                            Accessible.name: modelData.dateStr + ", " + modelData.percent + " percent"
                        }
                    }
                }
            }
        }
        }
    }

    Accessible.name: "Week overview"
    Accessible.role: Accessible.Pane
}
