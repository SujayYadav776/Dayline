import QtQuick

// Grouped settings card: a titled surface that sizes to its content column.
Rectangle {
    id: card
    required property string title
    default property alias content: col.data

    width: parent ? parent.width : 0
    height: col.implicitHeight + 2 * Theme.s16
    radius: Theme.radiusCard
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    Column {
        id: col
        x: Theme.s16
        y: Theme.s16
        width: card.width - 2 * Theme.s16
        spacing: Theme.s8

        Text {
            text: card.title
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sectionPx
            font.weight: Theme.weightHeading
            font.letterSpacing: Theme.headingTracking
        }
    }
}
