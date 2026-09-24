import QtQuick
import QtQuick.Controls

// shadcn/ui Select. Root is a ComboBox so callers use model / currentIndex /
// currentText / onActivated exactly as before — just swap `ComboBox` → `Select`.
ComboBox {
    id: control
    implicitHeight: 36

    contentItem: Text {
        leftPadding: Theme.s12
        rightPadding: control.indicator.width + Theme.s8
        text: control.displayText
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
        font.weight: Theme.weightLabel
        color: control.enabled ? Theme.text : Theme.textSecondary
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - Theme.s12
        y: (control.height - height) / 2
        text: "▾"
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.bodyPx
    }

    background: Rectangle {
        radius: Theme.radiusControl
        color: control.pressed || popup.visible ? Theme.surfaceAlt : Theme.surface
        border.color: control.activeFocus ? Theme.ring : Theme.input
        border.width: control.activeFocus ? Theme.ringWidth : 1
        Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
    }

    popup: Popup {
        id: popup
        y: control.height + Theme.s4
        width: control.width
        implicitHeight: contentItem.implicitHeight + 2 * Theme.s8
        padding: Theme.s8

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegate : null
            ScrollBar.vertical: ScrollBar {}
        }

        background: Rectangle {
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
        }
    }

    delegate: ItemDelegate {
        width: control.width
        height: 34
        contentItem: Text {
            text: modelData
            font.family: Theme.fontFamily
            font.pixelSize: Theme.bodyPx
            color: highlighted ? Theme.text : Theme.text
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: Theme.radiusControl
            color: highlighted ? Theme.surfaceAlt : "transparent"
        }
        highlighted: control.highlightedIndex === index
    }
}
