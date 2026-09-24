import QtQuick
import Dayline

// Spring-animated checkbox ported from React Bits' <SpringCheck /> (D-032).
// One spring scalar `progress` drives the whole choreography: the accent fill
// swells out of the box centre, the box itself overshoots on the bounce, and
// the tick draws itself via a dash-offset reveal. Press scales the box to 95%.
// Reduced motion (Theme.animate off) jumps straight to the end state.
Rectangle {
    id: box
    width: 20
    height: 20
    radius: width / 2
    color: "transparent"
    border.color: on ? Theme.accent : Theme.input
    border.width: 1.5
    clip: true

    property bool on: false
    // set true by the page when this row was just completed — plays the
    // spring from 0 instead of snapping (delegates are rebuilt on reload)
    property bool animateIn: false
    signal clicked()

    // the single spring scalar (may overshoot past 1)
    property real progress: on ? 1 : 0
    readonly property real held: Math.min(1, Math.max(0, progress))
    Behavior on progress {
        enabled: Theme.animate && box.armed
        SpringAnimation { spring: 3.5; damping: 0.5; mass: 0.7 }
    }
    property bool armed: false
    Component.onCompleted: {
        if (animateIn && Theme.animate) {
            progress = 0
            Qt.callLater(function () { box.armed = true; box.progress = 1 })
        } else {
            Qt.callLater(function () { box.armed = true })
        }
    }
    onOnChanged: progress = on ? 1 : 0

    // derived visuals (React's readings()): swell past full, box overshoot
    scale: (1 + Theme.boxSwell * Math.max(0, progress - 1)) * (area.pressed ? 0.95 : 1)

    // accent fill swelling from the centre (clipped by the box)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: parent.radius
        color: Theme.accent
        scale: Math.max(box.progress, 0)
    }

    // self-drawing tick: two rounded arms grow in sequence (short leg then
    // long stroke). Rectangles only — Item.clip does not clip Shape nodes
    // and ShapePath strokeColor is unreliable in this Qt build.
    Item {
        id: tick
        width: 14
        height: 14
        anchors.centerIn: parent
        readonly property real r1: Math.min(1, Math.max(0, (box.held - 0.35) / 0.25))
        readonly property real r2: Math.min(1, Math.max(0, (box.held - 0.55) / 0.32))
        Rectangle {
            x: 1
            y: 8
            width: 6.4 * tick.r1
            height: 2
            radius: 1
            color: Theme.accentInk
            transform: Rotation { origin.x: 0; origin.y: 1; angle: 45 }
        }
        Rectangle {
            x: 5
            y: 12
            width: 11.3 * tick.r2
            height: 2
            radius: 1
            color: Theme.accentInk
            transform: Rotation { origin.x: 0; origin.y: 1; angle: -45 }
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: box.clicked()
    }
    Accessible.role: Accessible.CheckBox
    Accessible.name: box.accessName
    Accessible.checked: box.on
    Accessible.onPressAction: box.clicked()
    property string accessName: ""
}
