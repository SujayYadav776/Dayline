import QtQuick
import QtQuick.Controls
import Dayline

// "Vault not found" recovery / first-run minimal chooser (§4.5).
// The full 3-step wizard arrives in M4; this gets users unstuck today.
Item {
    id: root
    required property var app        // AppViewModel

    Column {
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: 0
        width: Math.min(parent.width - 2 * Theme.s32, 420)
        spacing: Theme.s16

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Where do your daily notes live?"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.titlePx
            font.weight: Theme.weightHeading
            font.letterSpacing: Theme.titleTracking
            color: Theme.text
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Pick your Obsidian vault. Dayline only edits the To-Do section\nof your daily notes — everything else stays untouched."
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.bodyPx
        }

        // Detected vaults
        Column {
            visible: root.app.detectedVaults.length > 0
            width: parent.width
            spacing: Theme.s8

            Text {
                text: "Detected vaults"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.captionPx
            }
            Repeater {
                model: root.app.detectedVaults
                delegate: Rectangle {
                    width: parent.width
                    height: 48
                    radius: Theme.radiusControl
                    color: Theme.surface
                    border.color: Theme.border
                    border.width: 1
                    Row {
                        anchors.fill: parent
                        anchors.margins: Theme.s12
                        spacing: Theme.s8
                        Text {
                            width: parent.width - (defBadge.visible ? defBadge.width + Theme.s8 : 0)
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name + "  —  " + modelData.path
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.bodyPx
                            elide: Text.ElideMiddle
                        }
                        Rectangle {
                            id: defBadge
                            visible: modelData.isDefault
                            anchors.verticalCenter: parent.verticalCenter
                            width: dt.implicitWidth + Theme.s12
                            height: 20
                            radius: Theme.radiusChip
                            color: Theme.surfaceAlt
                            Text {
                                id: dt
                                anchors.centerIn: parent
                                text: "last open"
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.captionPx
                            }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.app.selectVault(modelData.path)
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: "Use vault " + modelData.name
                }
            }
        }

        // Manual path entry
        Row {
            width: parent.width
            spacing: Theme.s8

            Rectangle {
                width: parent.width - useBtn.width - folderBtn.width - 2 * Theme.s8
                height: 36
                radius: Theme.radiusControl
                color: Theme.surface
                border.color: pathField.activeFocus ? Theme.ring : Theme.input
                border.width: pathField.activeFocus ? Theme.ringWidth : 1
                TextInput {
                    id: pathField
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s12
                    anchors.rightMargin: Theme.s12
                    verticalAlignment: TextInput.AlignVCenter
                    clip: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    color: Theme.text
                    selectionColor: Theme.accent
                    cursorVisible: true
                    text: ""
                    onAccepted: root.app.selectVault(text)
                }
                Text {
                    visible: !pathField.text && !pathField.activeFocus
                    anchors.verticalCenter: parent.verticalCenter
                    x: Theme.s12
                    text: "…or paste a vault folder path"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                }
            }
            Rectangle {
                id: useBtn
                width: 92
                height: 36
                radius: Theme.radiusControl
                color: useMa.pressed ? Theme.accentHover : Theme.accent
                Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
                Text {
                    anchors.centerIn: parent
                    text: "Use vault"
                    color: Theme.accentInk
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    font.weight: Theme.weightLabel
                    font.letterSpacing: Theme.headingTracking
                }
                MouseArea {
                    id: useMa
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.app.selectVault(pathField.text)
                }
            }
            // no-Obsidian escape hatch: treat the pasted path as a plain folder
            Rectangle {
                id: folderBtn
                width: fb.implicitWidth + Theme.s24
                height: 36
                radius: Theme.radiusControl
                color: folderMa.pressed ? Theme.surfaceAlt : Theme.surface
                border.color: Theme.input
                border.width: 1
                Behavior on color { enabled: Theme.animate; ColorAnimation { duration: Theme.motionMs } }
                Text {
                    id: fb
                    anchors.centerIn: parent
                    text: "Use as folder"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    font.weight: Theme.weightLabel
                }
                MouseArea {
                    id: folderMa
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.app.selectFolder(pathField.text)
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Use pasted path as a plain folder"
            }
        }

        ErrorBanner {
            width: parent.width
            message: root.app.errorText
            onRetryRequested: root.app.retry()
        }
    }
}
