import QtQuick

// Small read-only metadata chip (📅 date, 🔁 rule, #tag).
Rectangle {
    id: chip
    required property string text
    width: label.implicitWidth + 2 * Theme.s8
    height: 22
    radius: Theme.radiusChip
    color: Theme.surfaceAlt
    border.color: Theme.border
    border.width: 1

    Text {
        id: label
        anchors.centerIn: parent
        text: chip.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.captionPx
        font.weight: Theme.weightLabel
        font.letterSpacing: Theme.headingTracking
        color: Theme.text
    }
}
