import QtQuick

// Friendly empty state (§4.5).
Column {
    id: root
    property string message: "No tasks yet."
    property string hint: ""
    spacing: Theme.s8
    width: parent ? parent.width : 0

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.message
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
        horizontalAlignment: Text.AlignHCenter
    }
    Text {
        visible: text.length > 0
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.hint
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.captionPx
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        width: parent.width
    }
}
