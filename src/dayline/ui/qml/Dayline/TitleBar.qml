import QtQuick
import QtQuick.Window
import Dayline

// Custom title bar for the frameless window: paper-transparent strip with
// macOS traffic-light dots (close · minimize · maximize) that grey out when
// the window is inactive, a faint serif wordmark, and a drag zone that uses
// the native system move (keeps Win+arrow snapping and drag-to-top snap).
Item {
    id: bar
    objectName: "titleBar"
    required property var win       // the ApplicationWindow
    height: 34

    // ---- drag zone (whole strip) ------------------------------------------
    MouseArea {
        anchors.fill: parent
        onPressed: (mouse) => {
            if (mouse.button === Qt.LeftButton)
                bar.win.startSystemMove()
        }
        onDoubleClicked: bar.toggleMaximized()
    }

    function toggleMaximized() {
        if (win.visibility === Window.Maximized)
            win.showNormal()
        else
            win.showMaximized()
    }

    // ---- faint wordmark -----------------------------------------------------
    Text {
        anchors.centerIn: parent
        text: "Dayline"
        font.family: Theme.serifFamily
        font.pixelSize: 12
        font.weight: Theme.weightLabel
        font.letterSpacing: 1
        color: Theme.textSecondary
        opacity: 0.55
    }

    // ---- traffic lights (top-right; close last) ---------------------------
    Row {
        id: dots
        objectName: "windowDots"
        anchors.right: parent.right
        anchors.rightMargin: Theme.s16
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.s8

        Repeater {
            model: [
                {"key": "min",   "color": "#FEBC2E", "edge": "#D89A22", "glyph": "–"},
                {"key": "max",   "color": "#28C840", "edge": "#1DA433", "glyph": bar.win.visibility === Window.Maximized ? "↔" : "+"},
                {"key": "close", "color": "#FF5F57", "edge": "#E0443E", "glyph": "✕"}
            ]
            delegate: Rectangle {
                id: dot
                required property var modelData
                width: 14
                height: 14
                radius: 7
                anchors.verticalCenter: parent.verticalCenter
                color: bar.win.active ? modelData.color : Theme.surfaceAlt
                border.color: bar.win.active ? modelData.edge : Theme.border
                border.width: 1
                Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }

                Text {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -1
                    text: dot.modelData.glyph
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: "#73000000"
                    opacity: dotMa.containsMouse && bar.win.active ? 1 : 0
                    Behavior on opacity { enabled: Theme.animate; NumberAnimation { duration: Theme.motionMs } }
                }

                MouseArea {
                    id: dotMa
                    anchors.fill: parent
                    anchors.margins: -3       // generous hit area
                    hoverEnabled: true
                    onClicked: {
                        if (dot.modelData.key === "close") bar.win.close()   // → tray per setting
                        else if (dot.modelData.key === "min") bar.win.showMinimized()
                        else bar.toggleMaximized()
                    }
                }
                Accessible.role: Accessible.Button
                Accessible.name: dot.modelData.key === "close" ? "Close"
                               : dot.modelData.key === "min" ? "Minimize" : "Maximize"
            }
        }
    }

    // hairline under the strip only while maximized (keeps it off the paper look)
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        visible: bar.win.visibility === Window.Maximized
        color: Theme.border
    }
}
