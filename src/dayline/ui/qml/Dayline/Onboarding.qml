import QtQuick
import QtQuick.Controls
import Dayline

// First-run wizard (§3.8): (1) pick vault, (2) confirm folder/format with a
// live preview, (3) optional autostart + hotkey. Ends on Today.
Item {
    id: ob
    required property var app        // AppViewModel
    property var vm: app.settingsVM
    property int step: 0
    property string chosenPath: vm.vaultPath || ""
    property bool folderPick: false  // step 1: skip Obsidian, use any folder

    readonly property var vaults: app.detectedVaults

    function finish() {
        if (chosenPath.length === 0) return
        if (folderPick)
            app.selectFolder(chosenPath)  // persists + builds store + starts
        else
            app.selectVault(chosenPath)   // persists + builds store + starts
    }

    Column {
        anchors.fill: parent
        spacing: Theme.s24

        // brand mark (exact logo)
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.s12
            Image {
                source: "../../assets/app.png"
                sourceSize.width: 44
                sourceSize.height: 44
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Dayline"
                font.family: Theme.serifFamily
                font.pixelSize: 24
                font.weight: Theme.weightHeading
                color: Theme.text
            }
        }

        // progress dots
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.s8
            Repeater {
                model: 3
                Rectangle {
                    width: 8; height: 8; radius: 4
                    color: index === ob.step ? Theme.accent : Theme.border
                }
            }
        }

        // ---- step 1: vault -------------------------------------------------
        Column {
            visible: ob.step === 0
            width: parent.width
            spacing: Theme.s16
            Text {
                text: "Where do your daily notes live?"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Theme.weightHeading
                font.letterSpacing: Theme.titleTracking
                color: Theme.text
                wrapMode: Text.Wrap
                width: parent.width
            }
            Text {
                text: ob.folderPick
                      ? "Pick any folder — Dayline stores your daily notes there\nas plain markdown (Daily/2026-09-24.md style). No Obsidian needed."
                      : "Dayline edits only the To-Do section of your daily notes."
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.bodyPx
                wrapMode: Text.Wrap
                width: parent.width
            }
            // source mode: Obsidian vault (default) or any plain folder
            Row {
                id: chipRow
                width: parent.width
                spacing: Theme.s8
                Repeater {
                    model: [
                        {"id": "obsidian", "label": "Obsidian vault"},
                        {"id": "folder", "label": "Any folder"}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: chipRow.width / 2 - Theme.s4
                        height: 34
                        radius: Theme.radiusControl
                        color: (ob.folderPick === (modelData.id === "folder")) ? Theme.surfaceAlt : Theme.surface
                        border.color: (ob.folderPick === (modelData.id === "folder")) ? Theme.accent : Theme.border
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.captionPx
                            font.weight: Theme.weightLabel
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ob.folderPick = modelData.id === "folder"
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Use " + modelData.label
                    }
                }
            }
            Repeater {
                model: ob.folderPick ? [] : ob.vaults
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 48
                    radius: Theme.radiusControl
                    color: ob.chosenPath === modelData.path ? Theme.surfaceAlt : Theme.surface
                    border.color: ob.chosenPath === modelData.path ? Theme.accent : Theme.border
                    border.width: 1
                    Row {
                        anchors.fill: parent
                        anchors.margins: Theme.s12
                        spacing: Theme.s8
                        Text {
                            width: parent.width - (badge.visible ? badge.width + Theme.s8 : 0)
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name + "  —  " + modelData.path
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.bodyPx
                            elide: Text.ElideMiddle
                        }
                        Rectangle {
                            id: badge
                            visible: modelData.isDefault
                            anchors.verticalCenter: parent.verticalCenter
                            width: bt.implicitWidth + Theme.s12
                            height: 20
                            radius: Theme.radiusChip
                            color: Theme.surface
                            Text { id: bt; anchors.centerIn: parent; text: "last open"; color: Theme.textSecondary; font.pixelSize: Theme.captionPx; font.family: Theme.fontFamily }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: ob.chosenPath = modelData.path
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: 36
                radius: Theme.radiusControl
                color: Theme.surface
                border.color: pathField.activeFocus ? Theme.ring : Theme.input
                border.width: pathField.activeFocus ? Theme.ringWidth : 1
                TextInput {
                    id: pathField
                    anchors.fill: parent
                    anchors.margins: Theme.s12
                    verticalAlignment: TextInput.AlignVCenter
                    clip: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                    color: Theme.text
                    text: ob.chosenPath
                    onTextChanged: ob.chosenPath = text
                }
            }
        }

        // ---- step 2: folder / format --------------------------------------
        Column {
            visible: ob.step === 1
            width: parent.width
            spacing: Theme.s12
            Text {
                text: "Confirm your daily-note setup"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Theme.weightHeading
                font.letterSpacing: Theme.titleTracking
                color: Theme.text
                wrapMode: Text.Wrap
                width: parent.width
            }
            SettingRow { label: "Folder" }
            Rectangle {
                width: parent.width; height: 36; radius: Theme.radiusControl
                color: Theme.surface
                border.color: folderField.activeFocus ? Theme.ring : Theme.input
                border.width: folderField.activeFocus ? Theme.ringWidth : 1
                TextInput {
                    id: folderField
                    anchors.fill: parent; anchors.margins: Theme.s12
                    verticalAlignment: TextInput.AlignVCenter; clip: true
                    text: ob.vm.folder
                    font.family: Theme.fontFamily; font.pixelSize: Theme.bodyPx; color: Theme.text
                    onEditingFinished: ob.vm.setFolder(text)
                }
            }
            SettingRow { label: "Date format" }
            Rectangle {
                width: parent.width; height: 36; radius: Theme.radiusControl
                color: Theme.surface
                border.color: formatField.activeFocus ? Theme.ring : Theme.input
                border.width: formatField.activeFocus ? Theme.ringWidth : 1
                TextInput {
                    id: formatField
                    anchors.fill: parent; anchors.margins: Theme.s12
                    verticalAlignment: TextInput.AlignVCenter; clip: true
                    text: ob.vm.dateFormat
                    font.family: Theme.fontFamily; font.pixelSize: Theme.bodyPx; color: Theme.text
                    onEditingFinished: ob.vm.setDateFormat(text)
                }
            }
            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "Today's note will be:\n" + ob.vm.todayPreview()
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.captionPx
            }
        }

        // ---- step 3: optional ---------------------------------------------
        Column {
            visible: ob.step === 2
            width: parent.width
            spacing: Theme.s12
            Text {
                text: "Almost done"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Theme.weightHeading
                font.letterSpacing: Theme.titleTracking
                color: Theme.text
            }
            Row {
                width: parent.width
                SettingRow { label: "Start with Windows"; width: parent.width - s1.width }
                Toggle { id: s1; anchors.verticalCenter: parent.verticalCenter; checked: ob.vm.autostart; onToggled: ob.vm.setAutostart(!checked) }
            }
            Row {
                width: parent.width
                SettingRow { label: "Enable global quick-add"; width: parent.width - s2.width }
                Toggle { id: s2; anchors.verticalCenter: parent.verticalCenter; checked: ob.vm.quickAddEnabled; onToggled: ob.vm.setQuickAddEnabled(!checked) }
            }
        }

        Item { width: 1; height: Theme.s8 }

        // ---- nav buttons ---------------------------------------------------
        Item {
            width: parent.width
            height: 36
            ActionButton {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Back"
                visible: ob.step > 0
                onClicked: ob.step = Math.max(0, ob.step - 1)
            }
            ActionButton {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                variant: "default"
                text: ob.step === 2 ? "Get started" : "Next"
                enabled: ob.step !== 0 || ob.chosenPath.length > 0
                onClicked: {
                    if (ob.step < 2) {
                        ob.step += 1
                    } else {
                        ob.finish()
                    }
                }
            }
        }
    }

    Accessible.name: "Onboarding"
    Accessible.role: Accessible.Pane
}
