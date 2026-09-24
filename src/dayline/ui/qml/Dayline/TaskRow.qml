import QtQuick
import Dayline

// One task line: priority dot, checkbox, inline-editable text, metadata chips,
// hover actions (edit / move-to-day / priority / delete) and the completion
// micro-animation. Mutations route through the App context property (FR-T1..T5).
Rectangle {
    id: row
    required property var task        // row dict from the viewmodel
    property bool showChecks: true
    property bool dimmed: false
    property bool selected: false
    property bool editing: false
    property bool celebrate: false    // play the tick-pop once (set by the page)
    signal toggledFromOpen(int key)   // lets the page mark the row to celebrate
    signal celebrateDone()            // page clears its celebrate key

    radius: Theme.radiusControl
    color: selected ? Theme.surfaceAlt : "transparent"
    height: content.implicitHeight + Theme.s8
    opacity: dimmed ? 0.62 : 1.0

    Component.onCompleted: {
        // the spring checkbox replays itself via animateIn; the old celebration
        // pulse ring ("wave") was removed by user request
        if (celebrate) Qt.callLater(row.celebrateDone)
    }

    // single-click delay so a double-click (jump to Obsidian) doesn't also
    // open the inline editor
    Timer {
        id: editTimer
        interval: 280
        onTriggered: row.beginEdit()
    }

    function cyclePriority() {
        var order = ["", "high", "medium", "low"]
        var i = order.indexOf(task.priority || "")
        App.setPriority(task.taskKey, order[(i + 1) % order.length])
    }

    function beginEdit() {
        if (task.statusKind === "done" || task.statusKind === "moved"
                || task.statusKind === "cancelled")
            return
        row.editing = true
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Row {
        id: content
        x: Theme.s8 + (task.indentLevel || 0) * Theme.s16
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.s8

        // priority dot — only shown when a priority exists (the empty grey
        // circle was noise; without it the checkbox leads the row and the
        // completion ring clearly originates from the tick box)
        Rectangle {
            visible: !!task.priority
            width: 20
            height: 20
            radius: 10
            anchors.verticalCenter: parent.verticalCenter
            color: "transparent"
            Rectangle {
                anchors.centerIn: parent
                width: 10
                height: 10
                radius: 5
                color: Theme.prioColor(task.priority)
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: row.cyclePriority()
            }
            Accessible.role: Accessible.Button
            Accessible.name: "Priority: " + task.priority
        }

        // checkbox — SpringCheck port: spring fill swell + self-drawn tick
        SpringBox {
            id: box
            anchors.verticalCenter: parent.verticalCenter
            visible: row.showChecks
            on: task.statusKind === "done"
            animateIn: row.celebrate
            accessName: task.description
            onClicked: {
                if (!box.on) row.toggledFromOpen(task.taskKey)
                App.toggleTask(task.taskKey)
            }
        }

        Column {
            id: textCol
            width: row.width - x - Theme.s24 - (actions.width + Theme.s8)
            spacing: Theme.s4

            Text {
                id: bodyText
                visible: !row.editing
                width: parent.width
                text: (task.statusKind === "moved" ? "→ " : "") + task.description
                font.family: Theme.fontFamily
                font.pixelSize: Theme.bodyPx
                wrapMode: Text.Wrap
                property bool strikethrough:
                    task.statusKind === "done" || task.statusKind === "cancelled"
                // SpringCheck word dim: ink fades to doneOpacity on the spring;
                // the wipe rule handles the strike for single lines, wrapped
                // labels keep the static strikeout (one rule can't cross lines)
                readonly property bool springStrike:
                    row.showChecks && task.statusKind === "done" && lineCount === 1
                color: row.showChecks && task.statusKind === "done"
                       ? Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b,
                                 1 - (1 - Theme.doneOpacity) * box.held)
                       : (strikethrough ? Theme.textSecondary : Theme.text)
                font.strikeout: strikethrough && !springStrike

                // strike-through wipe across exactly the label's width,
                // lagging behind the fill (React's readings().rule)
                Rectangle {
                    visible: bodyText.springStrike
                    x: 0
                    y: bodyText.height * 0.54
                    width: bodyText.paintedWidth * Math.min(1, Math.max(0,
                               (box.held - Theme.strikeLag)
                               / (Theme.ruleEnd - Theme.strikeLag)))
                    height: Math.max(1.5, Math.round(Theme.bodyPx / 6) / 2)
                    radius: 2
                    color: Theme.text
                    opacity: 0.55
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    // single click → edit inline (debounced by editTimer);
                    // double click cancels the editor and jumps to Obsidian
                    onClicked: editTimer.restart()
                    onDoubleClicked: {
                        editTimer.stop()
                        App.openTaskInObsidian(task.taskKey)
                    }
                }
            }

            Rectangle {
                visible: row.editing
                width: parent.width
                height: Math.max(editField.contentHeight + Theme.s8, 30)
                radius: Theme.radiusControl
                color: Theme.surface
                border.color: Theme.accent
                border.width: 1
                TextInput {
                    id: editField
                    anchors.fill: parent
                    anchors.margins: Theme.s4
                    verticalAlignment: TextInput.AlignVCenter
                    clip: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    color: Theme.text
                    selectionColor: Theme.accent
                    text: task.description
                    onEditingFinished: {
                        App.editTask(task.taskKey, text)
                        row.editing = false
                    }
                    Keys.onEscapePressed: row.editing = false
                }
            }

            Row {
                visible: chips.children.length > 0
                spacing: Theme.s4
                Repeater {
                    id: chips
                    model: task.chips || []
                    delegate: Chip {
                        required property var modelData
                        text: modelData
                    }
                }
            }
        }

        // hover actions
        Row {
            id: actions
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.s4
            opacity: rowHover.containsMouse || row.editing ? 1 : 0
            visible: opacity > 0.01
            Behavior on opacity { NumberAnimation { duration: Theme.motionMs } }

            Repeater {
                model: [
                    {"icon": "✎", "name": "Edit", "act": "edit"},
                    {"icon": "📆", "name": "Move to day", "act": "move"},
                    {"icon": "", "name": "Priority", "act": "prio"},
                    {"icon": "✕", "name": "Delete", "act": "del"}
                ]
                delegate: Rectangle {
                    width: 26
                    height: 26
                    radius: Theme.radiusControl
                    color: actMouse.pressed ? Theme.border : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: modelData.icon
                        color: modelData.act === "del" ? Theme.danger : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                    }
                    MouseArea {
                        id: actMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.act === "edit") row.beginEdit()
                            else if (modelData.act === "prio") row.cyclePriority()
                            else if (modelData.act === "move") {
                                var w = row.Window.window
                                if (w) w.openMoveMenu(task.taskKey, task.description)
                            }
                            else App.deleteTask(task.taskKey)
                        }
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.name
                }
            }
        }
    }

    MouseArea {
        id: rowHover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    onEditingChanged: if (editing) editField.forceActiveFocus()
    Accessible.name: task.description
    Accessible.role: Accessible.ListItem
}
