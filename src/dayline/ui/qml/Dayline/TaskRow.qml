import QtQuick

// One task line: priority dot, checkbox visual, text, chips, age/carry hints.
// Read-only in M2; interactive affordances arrive in M3.
Rectangle {
    id: row
    required property var task      // model view
    property bool showChecks: true
    property bool dimmed: false

    radius: Theme.radiusControl
    color: "transparent"
    height: content.implicitHeight + Theme.s8
    opacity: dimmed ? 0.62 : 1.0

    Row {
        id: content
        x: Theme.s8 + task.indentLevel * Theme.s16
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.s8

        // priority dot (also has a tooltip-ish text fallback — not colour-only, §4.7)
        Rectangle {
            width: 10
            height: 10
            radius: 5
            anchors.verticalCenter: parent.verticalCenter
            color: task.priority ? Theme.prioColor(task.priority) : "transparent"
            border.color: task.priority ? color : Theme.prioNone
            border.width: task.priority ? 0 : 1.5
        }

        Rectangle {
            width: 18
            height: 18
            radius: 5
            anchors.verticalCenter: parent.verticalCenter
            visible: row.showChecks
            color: doneFill ? Theme.accent : "transparent"
            border.color: doneFill ? Theme.accent : Theme.prioNone
            border.width: 1.5
            property bool doneFill: task.statusKind === "done"
            Text {
                anchors.centerIn: parent
                visible: parent.doneFill
                text: "✓"
                color: Theme.surface
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.Bold
            }
        }

        Column {
            id: textCol
            width: row.width - x - Theme.s24
            spacing: Theme.s4

            Text {
                width: parent.width
                text: (task.statusKind === "moved" ? "→ " : "") + task.description
                font.family: Theme.fontFamily
                font.pixelSize: Theme.bodyPx
                color: strikethrough ? Theme.textSecondary : Theme.text
                wrapMode: Text.Wrap
                property bool strikethrough:
                    task.statusKind === "done" || task.statusKind === "cancelled"
                font.strikeout: strikethrough
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
    }
}
