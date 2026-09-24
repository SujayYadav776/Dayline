import QtQuick

// Inline non-blocking error banner with retry (§4.5).
Rectangle {
    id: banner
    required property string message
    signal retryRequested()

    visible: message.length > 0
    width: parent ? parent.width : 0
    height: Math.max(inner.implicitHeight + 2 * Theme.s12, 44)
    radius: Theme.radiusControl
    color: Qt.alpha(Theme.danger, dark ? 0.16 : 0.08)
    border.color: Qt.alpha(Theme.danger, 0.4)
    border.width: 1

    Row {
        id: inner
        anchors.fill: parent
        anchors.margins: Theme.s12
        spacing: Theme.s8

        Text {
            width: parent.width - retry.width - parent.spacing
            text: banner.message
            wrapMode: Text.Wrap
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.bodyPx
        }
        Rectangle {
            id: retry
            width: retryText.implicitWidth + Theme.s16
            height: 28
            radius: Theme.radiusControl
            color: Theme.surface
            border.color: Theme.border
            Text {
                id: retryText
                anchors.centerIn: parent
                text: "Retry"
                color: Theme.accent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.captionPx
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: banner.retryRequested()
            }
        }
    }
}
