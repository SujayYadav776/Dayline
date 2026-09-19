import QtQuick

// Label + read-only value row for settings summaries.
Row {
    required property string label
    required property string value
    width: parent ? parent.width : 0
    spacing: Theme.s8
    Text {
        text: label
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
    }
    Text {
        width: parent.width - x - Theme.s8
        text: ": " + value
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
        elide: Text.ElideMiddle
    }
}
