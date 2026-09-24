import QtQuick

// Collapsible section header with count badge.
Rectangle {
    id: header
    required property string title
    property int count: 0
    property bool expanded: true
    signal toggled()

    width: parent ? parent.width : 0
    height: 34
    radius: Theme.radiusControl
    color: "transparent"

    Row {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.s8

        Text {
            id: chevron
            text: header.expanded ? "▾" : "▸"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.bodyPx
            anchors.verticalCenter: parent.verticalCenter
            Behavior on rotation { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs } }
        }
        Text {
            text: header.title
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sectionPx
            font.weight: Theme.weightHeading
            font.letterSpacing: Theme.headingTracking
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            visible: header.count > 0
            width: badge.implicitWidth + Theme.s12
            height: 20
            radius: Theme.radiusChip
            color: Theme.surfaceAlt
            anchors.verticalCenter: parent.verticalCenter
            Text {
                id: badge
                anchors.centerIn: parent
                text: header.count
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.captionPx
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            header.toggled()
        }
    }
    Accessible.role: Accessible.Button
    Accessible.name: header.title + ", " + (header.expanded ? "expanded" : "collapsed")
}
