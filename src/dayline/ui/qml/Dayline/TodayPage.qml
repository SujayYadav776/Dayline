import QtQuick
import QtQuick.Controls
import Dayline

// Today page: header nav, add bar, progress card, three sections (M3 interactive).
Item {
    id: page
    required property var vm      // App.todayVM

    property int todoIndex: -1
    property int editKey: -1

    function selectedKey() {
        return page.todoIndex >= 0 && page.todoIndex < vm.todoList.length
               ? vm.todoList[page.todoIndex].taskKey : -1
    }
    function clampSelection() {
        var n = vm.todoList.length
        if (page.todoIndex >= n)
            page.todoIndex = n - 1
    }
    function focusAdd() {
        addField.forceActiveFocus()
    }

    onVisibleChanged: if (visible) Qt.callLater(page.focusAdd)

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

        // ---- add bar (FR-T1, FR-T8) -------------------------------------------
        Row {
            width: parent.width
            spacing: Theme.s8

            Rectangle {
                width: parent.width - addBtn.width - parent.spacing
                height: 40
                radius: Theme.radiusControl
                color: Theme.surface
                border.color: addField.activeFocus ? Theme.accent : Theme.border
                border.width: 1
                TextInput {
                    id: addField
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s12
                    anchors.rightMargin: Theme.s12
                    anchors.verticalCenter: parent.verticalCenter
                    verticalAlignment: TextInput.AlignVCenter
                    clip: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    color: Theme.text
                    selectionColor: Theme.accent
                    cursorVisible: true
                    text: ""
                    onAccepted: submit()
                    function submit() {
                        var t = text.trim()
                        if (t.length > 0) {
                            App.addTask(t)
                            addField.text = ""
                            page.todoIndex = 0
                        }
                    }
                    Keys.onReturnPressed: submit()
                    Keys.onEnterPressed: submit()
                }
                Text {
                    visible: !addField.text && !addField.activeFocus
                    anchors.verticalCenter: parent.verticalCenter
                    x: Theme.s12
                    text: "Add a task…  (! !! !!! = low / med / high)"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                }
            }

            Rectangle {
                id: addBtn
                width: 60
                height: 40
                radius: Theme.radiusControl
                color: addField.text.trim().length > 0 ? Theme.accent : Theme.surfaceAlt
                Text {
                    anchors.centerIn: parent
                    text: "Add"
                    color: addField.text.trim().length > 0 ? Theme.onAccent : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    font.weight: Font.DemiBold
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: addField.submit()
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Add task"
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
                            id: todoRepeater
                            model: page.vm.todoList
                            delegate: TaskRow {
                                required property var modelData
                                required property int index
                                width: parent ? parent.width : 0
                                task: modelData
                                selected: index === page.todoIndex
                                Accessible.name: modelData.description
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

    // ---- keyboard on the To-do list (§4.6) ----------------------------------
    function moveSelection(delta) {
        var n = vm.todoList.length
        if (n === 0) { page.todoIndex = -1; return }
        page.todoIndex = Math.max(0, Math.min(n - 1, page.todoIndex < 0 ? 0 : page.todoIndex + delta))
    }
    function editingField() {
        return addField.activeFocus || (todoRepeater.itemAt(page.todoIndex)
               && todoRepeater.itemAt(page.todoIndex).editing)
    }

    Shortcut { sequence: "Down"; enabled: page.visible
        onActivated: if (!page.editingField()) page.moveSelection(1) }
    Shortcut { sequence: "Up"; enabled: page.visible
        onActivated: if (!page.editingField()) page.moveSelection(-1) }
    Shortcut { sequence: "Space"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.toggleTask(k) } }
    Shortcut { sequence: "F2"; enabled: page.visible
        onActivated: { var it = todoRepeater.itemAt(page.todoIndex); if (it) it.beginEdit() } }
    Shortcut { sequence: "Delete"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.deleteTask(k) } }
    Shortcut { sequence: "1"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.setPriority(k, "high") } }
    Shortcut { sequence: "2"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.setPriority(k, "medium") } }
    Shortcut { sequence: "3"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.setPriority(k, "low") } }
    Shortcut { sequence: "0"; enabled: page.visible && !page.editingField()
        onActivated: { var k = page.selectedKey(); if (k >= 0) App.setPriority(k, "") } }
    Shortcut { sequence: "Alt+Down"; enabled: page.visible
        onActivated: { var k = page.selectedKey()
            if (k >= 0 && page.todoIndex < vm.todoList.length - 1)
                App.moveTask(k, vm.todoList[page.todoIndex + 1].taskKey) } }
    Shortcut { sequence: "Alt+Up"; enabled: page.visible
        onActivated: { var k = page.selectedKey()
            if (k >= 0 && page.todoIndex > 0)
                App.moveTask(k, vm.todoList[page.todoIndex - 1].taskKey) } }

    Accessible.name: "Today page"
    Accessible.role: Accessible.Pane
}
