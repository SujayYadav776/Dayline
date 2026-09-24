import QtQuick

// A small label used above/next to a control inside a settings card (shadcn Label).
Text {
    required property string label
    width: parent ? parent.width : 0
    text: label
    color: Theme.text
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodyPx
    font.weight: Theme.weightLabel
    font.letterSpacing: Theme.headingTracking
    verticalAlignment: Text.AlignVCenter
    topPadding: Theme.s4
}
