import QtQuick
import QtQuick.Window
import Dayline

// M0 packaging-spike window: proves Theme + QML boot in dev and frozen builds.
// Replaced by the real shell (navigation, Today page) in M2.
Window {
    id: root
    objectName: "rootWindow"
    property bool qmlReady: false

    visible: true
    width: 440
    height: 720
    minimumWidth: 360
    minimumHeight: 480
    title: "Dayline"
    color: Theme.bg

    Component.onCompleted: root.qmlReady = true

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s24
        spacing: Theme.s24

        Text {
            text: "Dayline"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.titlePx
            font.weight: Font.DemiBold
            color: Theme.text
        }

        // Progress card with a hand-drawn ring (no Controls dependency).
        Rectangle {
            id: card
            width: parent.width
            height: 120
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: Theme.s16
                spacing: Theme.s16

                Item {
                    id: ring
                    width: 88
                    height: 88
                    property real value: 0.68

                    Canvas {
                        id: ringCanvas
                        anchors.fill: parent
                        antialiasing: true
                        property real value: ring.value
                        onValueChanged: requestPaint()
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.reset()
                            var lw = 7
                            var c = width / 2
                            var r = (Math.min(width, height) - lw) / 2
                            ctx.lineWidth = lw
                            ctx.lineCap = "round"
                            ctx.strokeStyle = Theme.surfaceAlt
                            ctx.beginPath()
                            ctx.arc(c, c, r, 0, Math.PI * 2)
                            ctx.stroke()
                            ctx.strokeStyle = Theme.accent
                            ctx.beginPath()
                            ctx.arc(c, c, r, -Math.PI / 2,
                                    -Math.PI / 2 + Math.PI * 2 * value)
                            ctx.stroke()
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: Math.round(ring.value * 100) + "%"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.bodyPx
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                }

                Column {
                    width: parent.width - ring.width - parent.spacing
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.s4

                    Text {
                        text: "13 of 19 done"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sectionPx
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Text {
                        text: "UI foundations online — Today page lands in M2"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }
                }
            }
        }
    }
}
