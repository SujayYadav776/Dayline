import QtQuick
import Dayline

// One task line: priority dot, checkbox, inline-editable text, metadata chips,
// and hover actions. Mutations route through the App context property (FR-T1..T5).
Rectangle {
    id: row
    required property var task        // row dict from the viewmodel
    property bool showChecks: true
    property bool dimmed: false
    property bool selected: false
    property bool editing: false

    radius: Theme.radiusControl
    color: selected ? Theme.surfaceAlt : "transparent"
    height: content.implicitHeight + Theme.s8
    opacity: dimmed ? 0.62 : 1.0

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

        // priority dot (click to cycle) — also exposed via Accessible.name text
        Rectangle {
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
                color: task.priority ? Theme.prioColor(task.priority) : "transparent"
                border.color: task.priority ? color : Theme.prioNone
                border.width: task.priority ? 0 : 1.5
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: row.cyclePriority()
            }
            Accessible.role: Accessible.Button
            Accessible.name: "Priority: " + (task.priority || "none")
        }

        // checkbox
        Rectangle {
            id: box
            width: 18
            height: 18
            radius: 5
            anchors.verticalCenter: parent.verticalCenter
            visible: row.showChecks
            property bool doneFill: task.statusKind === "done"
            color: doneFill ? Theme.accent : "transparent"
            border.color: doneFill ? Theme.accent : Theme.prioNone
            border.width: 1.5
            Text {
                anchors.centerIn: parent
                visible: box.doneFill
                text: "✓"
                color: Theme.onAccent
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.Bold
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: App.toggleTask(task.taskKey)
            }
            Accessible.role: Accessible.CheckBox
            Accessible.name: task.description
            Accessible.checked: box.doneFill
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
                color: strikethrough ? Theme.textSecondary : Theme.text
                wrapMode: Text.Wrap
                property bool strikethrough:
                    task.statusKind === "done" || task.statusKind === "cancelled"
                font.strikeout: strikethrough
                MouseArea {
                    anchors.fill: parent
                    onDoubleClicked: row.beginEdit()
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
