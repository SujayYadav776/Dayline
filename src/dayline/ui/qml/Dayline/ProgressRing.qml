import QtQuick

// Animated determinate progress ring (no Controls dependency).
Item {
    id: root
    implicitWidth: 96
    implicitHeight: 96

    required property real value        // 0..1, may bind to a live property
    property string label: ""
    property int lineWidth: 8
    property color trackColor: Theme.surfaceAlt
    property color progressColor: Theme.accent

    // eased internal value drives the paint (≤ 250 ms, FR-D1)
    QtObject {
        id: anim
        property real v: root.value
        function set(target) {
            if (!Theme.animate) { v = target; return }
            animRun.to = target
            animRun.start()
        }
        onVChanged: canvas.requestPaint()
    }
    NumberAnimation {
        id: animRun
        target: anim
        property: "v"
        duration: Theme.ringMotionMs
        easing.type: Easing.OutCubic
    }
    onValueChanged: anim.set(value)
    Component.onCompleted: anim.v = value

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var lw = root.lineWidth
            var c = Math.min(width, height) / 2
            var r = c - lw / 2 - 1
            ctx.lineWidth = lw
            ctx.lineCap = "round"
            ctx.strokeStyle = root.trackColor
            ctx.beginPath()
            ctx.arc(c, c, r, 0, Math.PI * 2)
            ctx.stroke()
            if (anim.v > 0.0001) {
                ctx.strokeStyle = root.progressColor
                ctx.beginPath()
                ctx.arc(c, c, r, -Math.PI / 2,
                        -Math.PI / 2 + Math.PI * 2 * Math.min(anim.v, 1))
                ctx.stroke()
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Column {
        anchors.centerIn: parent
        spacing: 0
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(root.value * 100) + "%"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sectionPx
            font.weight: Font.DemiBold
            color: Theme.text
        }
        Text {
            visible: root.label !== ""
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            font.family: Theme.fontFamily
            font.pixelSize: Theme.captionPx
            color: Theme.textSecondary
        }
    }
}
