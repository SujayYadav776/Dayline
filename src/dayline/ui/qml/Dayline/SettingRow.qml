import QtQuick

// A small secondary label used above a control inside a settings card.
Text {
    required property string label
    width: parent ? parent.width : 0
    text: label
    color: Theme.textSecondary
    font.family: Theme.fontFamily
    font.pixelSize: Theme.captionPx
    topPadding: Theme.s4
}
