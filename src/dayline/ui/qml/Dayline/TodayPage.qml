import QtQuick
import QtQuick.Controls
import Dayline

// Today page (paper mockup): the big lowercase-day / pixel-date / month block,
// one flat task list (completed tasks inline, ticked + struck-through), and a
// rounded quick-add pill anchored at the bottom of the page.
Item {
    id: page
    required property var vm      // App.todayVM

    property int todoIndex: -1
    property int editKey: -1
    property int celebrateKey: -1   // task key whose row should pop once (completion)

    function selectedKey() {
        return page.todoIndex >= 0 && page.todoIndex < vm.tasksList.length
               ? vm.tasksList[page.todoIndex].taskKey : -1
    }
    function clampSelection() {
        var n = vm.tasksList.length
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
        anchors.bottomMargin: Theme.s24
        spacing: Theme.s8

        // ---- date block -------------------------------------------------------
        Column {
            id: dateBlock
            objectName: "dateBlock"
            width: parent.width
            topPadding: Theme.s8
            spacing: Theme.s4

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: page.vm.dayName
                font.family: Theme.fontFamily
                font.pixelSize: Theme.dayPx
                font.weight: Theme.weightHeading
                color: Theme.text
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: page.vm.dayNum
                font.family: Theme.pixelFamily
                font.pixelSize: Theme.datePx
                color: Theme.text
                height: paintedHeight + 4
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: page.vm.monthName
                font.family: Theme.fontFamily
                font.pixelSize: Theme.monthPx
                font.weight: Theme.weightHeading
                color: Theme.text
            }
        }

        // ---- error banner -----------------------------------------------------
        ErrorBanner {
            message: page.vm.errorText
            onRetryRequested: page.vm.retryRequested()
        }

        // ---- one flat list: open → carried → done (ticked + struck) ------------
        Flickable {
            width: parent.width
            height: parent.height - y - addRow.height - parent.spacing - Theme.s8
            clip: true
            contentHeight: stack.implicitHeight + Theme.s16
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            Column {
                id: stack
                width: parent.width
                spacing: 2

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
                    spacing: 2
                    Repeater {
                        id: todoRepeater
                        model: page.vm.tasksList
                        delegate: TaskRow {
                            required property var modelData
                            required property int index
                            width: parent ? parent.width : 0
                            task: modelData
                            selected: index === page.todoIndex
                            celebrate: modelData.taskKey === page.celebrateKey
                                       && modelData.statusKind === "done"
                            onToggledFromOpen: (key) => page.celebrateKey = key
                            onCelebrateDone: page.celebrateKey = -1
                            Accessible.name: modelData.description
                        }
                    }
                }

                Text {
                    visible: !page.vm.loading && !page.vm.errorText
                             && page.vm.tasksList.length === 0
                    objectName: "emptyHint"
                    anchors.horizontalCenter: parent.horizontalCenter
                    topPadding: Theme.s32
                    text: "No tasks on this day."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    color: Theme.text
                }
            }
        }

        // ---- quick-add pill (FR-T1, FR-T8) --------------------------------------
        Row {
            id: addRow
            objectName: "addRow"
            width: parent.width
            spacing: Theme.s12

            Rectangle {
                width: parent.width - addBtn.width - parent.spacing
                height: 44
                radius: 22
                color: Theme.surface
                border.color: addField.activeFocus ? Theme.accent : Theme.border
                border.width: addField.activeFocus ? 1.5 : 1
                Behavior on border.color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }

                TextInput {
                    id: addField
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s16
                    anchors.rightMargin: Theme.s16
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
                    x: Theme.s16
                    text: "Add a task…  (! !! !!! = low / med / high)"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                }
            }

            Rectangle {
                id: addBtn
                objectName: "addButton"
                width: 44
                height: 44
                radius: 22
                color: addField.text.trim().length > 0
                       ? (addBtnMa.pressed ? Theme.accentHover : Theme.accent) : Theme.surface
                border.color: addField.text.trim().length > 0 ? color : Theme.border
                border.width: addField.text.trim().length > 0 ? 0 : 1
                Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
                Text {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -1
                    text: "+"
                    color: addField.text.trim().length > 0 ? Theme.accentInk : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 22
                    font.weight: Theme.weightLabel
                }
                MouseArea {
                    id: addBtnMa
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: addField.submit()
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Add task"
            }
        }
    }

    // ---- keyboard on the task list (§4.6) ----------------------------------
    function moveSelection(delta) {
        var n = vm.tasksList.length
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
            if (k >= 0 && page.todoIndex < vm.tasksList.length - 1)
                App.moveTask(k, vm.tasksList[page.todoIndex + 1].taskKey) } }
    Shortcut { sequence: "Alt+Up"; enabled: page.visible
        onActivated: { var k = page.selectedKey()
            if (k >= 0 && page.todoIndex > 0)
                App.moveTask(k, vm.tasksList[page.todoIndex - 1].taskKey) } }

    Accessible.name: "Today page"
    Accessible.role: Accessible.Pane
}
