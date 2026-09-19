import QtQuick
import QtQuick.Controls
import Dayline

// Today page (M2, read-only): header nav, progress card, three sections.
Item {
    id: page
    required property var vm      // App.todayVM

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
                anchors.top: parent.top
                spacing: Theme.s8

                Repeater {
                    model: ["‹", "›"]
                    delegate: Rectangle {
                        width: 32
                        height: 32
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
                            onClicked: modelData === "‹" ? page.vm.prevDayRequested()
                                                          : page.vm.nextDayRequested()
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData === "‹" ? "Previous day" : "Next day"
                    }
                }
            }

            Row {
                id: chips
                anchors.right: parent.right
                anchors.verticalCenter: nav.verticalCenter
                spacing: Theme.s8

                Rectangle {
                    id: todayChip
                    visible: !page.vm.isToday
                    width: tc.implicitWidth + Theme.s16
                    height: 24
                    radius: Theme.radiusChip
                    color: Theme.surfaceAlt
                    border.color: Theme.border
                    Text {
                        id: tc
                        anchors.centerIn: parent
                        text: "Today"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: page.vm.goTodayRequested()
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: "Back to today"
                }
                Rectangle {
                    id: carriedChip
                    visible: page.vm.carriedOver > 0
                    width: cc.implicitWidth + Theme.s16
                    height: 24
                    radius: Theme.radiusChip
                    color: Theme.dark ? "#233024" : "#EAF6EF"
                    border.color: Theme.success
                    Text {
                        id: cc
                        anchors.centerIn: parent
                        text: "Carried over: " + page.vm.carriedOver
                        color: Theme.success
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                    }
                }
            }

            Text {
                anchors.left: nav.right
                anchors.right: chips.left
                anchors.leftMargin: Theme.s12
                anchors.rightMargin: Theme.s12
                anchors.verticalCenter: nav.verticalCenter
                text: page.vm.dateLabel
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Font.DemiBold
                color: Theme.text
                elide: Text.ElideRight
            }
        }

        // ---- error banner ---------------------------------------------------
        ErrorBanner {
            message: page.vm.errorText
            onRetryRequested: page.vm.retryRequested()
        }

        // ---- progress card ----------------------------------------------------
        Rectangle {
            visible: page.vm.loading || page.vm.hasTasks
            width: parent.width
            height: 104
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: Theme.s16
                spacing: Theme.s16

                ProgressRing {
                    id: ring
                    width: 72
                    height: 72
                    anchors.verticalCenter: parent.verticalCenter
                    value: page.vm.progress
                }
                Column {
                    width: parent.width - ring.width - parent.spacing
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.s4
                    Text {
                        text: page.vm.loading
                              ? "…"
                              : page.vm.doneCount + " of " + page.vm.totalCount + " done"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sectionPx
                        font.weight: Font.DemiBold
                    }
                    Text {
                        visible: !page.vm.loading && page.vm.totalCount > 0
                        text: page.vm.percent + "% complete"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                    }
                }
            }
        }

        // ---- sections / states -----------------------------------------------
        Flickable {
            width: parent.width
            height: parent.height - y - Theme.s8
            clip: true
            contentHeight: stack.implicitHeight + 40
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            Column {
                id: stack
                width: parent.width
                spacing: Theme.s8

                Column {
                    visible: page.vm.loading
                    width: parent.width
                    spacing: Theme.s12
                    Repeater {
                        model: 4
                        SkeletonItem { width: parent.width - (index % 2) * Theme.s32 }
                    }
                }

                Column {
                    visible: !page.vm.loading && !page.vm.errorText
                    width: parent.width
                    spacing: Theme.s8

                    SectionHeader {
                        id: todoHeader
                        title: "To do"
                        count: page.vm.todoCount
                    }
                    Column {
                        width: parent.width
                        spacing: 2
                        Repeater {
                            model: page.vm.todoList
                            delegate: TaskRow {
                                required property var modelData
                                width: parent ? parent.width : 0
                                task: modelData
                            }
                        }
                        EmptyState {
                            visible: !page.vm.loading && page.vm.todoCount === 0
                            message: "Nothing to do — enjoy the calm."
                        }
                    }

                    SectionHeader {
                        id: doneHeader
                        title: "Done"
                        count: page.vm.doneSectionCount
                        expanded: false
                    }
                    Column {
                        width: parent.width
                        visible: doneHeader.expanded
                        spacing: 2
                        Repeater {
                            model: page.vm.doneList
                            delegate: TaskRow {
                                required property var modelData
                                width: parent ? parent.width : 0
                                task: modelData
                                dimmed: true
                            }
                        }
                    }

                    SectionHeader {
                        id: carriedHeader
                        title: "Carried forward"
                        count: page.vm.carriedSectionCount
                        expanded: false
                    }
                    Column {
                        width: parent.width
                        visible: carriedHeader.expanded
                        spacing: 2
                        Repeater {
                            model: page.vm.carriedList
                            delegate: TaskRow {
                                required property var modelData
                                width: parent ? parent.width : 0
                                task: modelData
                                showChecks: false
                                dimmed: true
                            }
                        }
                    }
                }
            }
        }
    }

    Accessible.name: "Today page"
    Accessible.role: Accessible.Pane
}
