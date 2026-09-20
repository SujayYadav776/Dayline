import QtQuick
import QtQuick.Controls
import Dayline

// Settings (PRD §3.7): grouped cards, all changes apply live.
Item {
    id: page
    required property var vm      // App.settingsVM
    property var app              // AppViewModel (runRollover / change vault)

    Flickable {
        anchors.fill: parent
        contentHeight: col.implicitHeight + Theme.s32
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        Column {
            id: col
            x: Theme.s24
            width: page.width - 2 * Theme.s24
            spacing: Theme.s16

            Text {
                text: "Settings"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.titlePx
                font.weight: Font.DemiBold
                color: Theme.text
            }

            // ---- Appearance ------------------------------------------------
            Card {
                title: "Appearance"
                SettingRow { label: "Theme" }
                ComboBox {
                    width: parent.width
                    model: ["system", "light", "dark"]
                    currentIndex: ["system", "light", "dark"].indexOf(page.vm.theme)
                    onActivated: page.vm.setTheme(currentText)
                }
                SettingRow { label: "Sort tasks by" }
                ComboBox {
                    width: parent.width
                    model: ["priority", "manual"]
                    currentIndex: page.vm.sortMode === "manual" ? 1 : 0
                    onActivated: page.vm.setSortMode(currentText)
                }
                SettingRow { label: "Week starts on" }
                ComboBox {
                    width: parent.width
                    model: ["Monday", "Sunday"]
                    currentIndex: page.vm.weekStart === "sun" ? 1 : 0
                    onActivated: page.vm.setWeekStart(currentText === "Sunday" ? "sun" : "mon")
                }
                Row {
                    width: parent.width
                    visible: page.app && page.app.micaSupported
                    SettingRow { label: "Mica backdrop"; width: parent.width - micw.width }
                    Switch {
                        id: micw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.mica
                        onToggled: page.vm.setMica(checked)
                    }
                }
            }

            // ---- Obsidian --------------------------------------------------
            Card {
                title: "Obsidian vault"
                Labeled { label: "Vault"; value: page.vm.vaultPath || "(none)" }
                Labeled { label: "Folder"; value: page.vm.folder }
                Labeled { label: "Date format"; value: page.vm.dateFormat }
                Labeled { label: "Heading"; value: page.vm.heading }
                Rectangle {
                    visible: page.vm.unsupportedFormat
                    width: parent.width
                    height: warn.implicitHeight + Theme.s16
                    radius: Theme.radiusControl
                    color: Theme.dark ? "#3A2324" : "#FDECEC"
                    border.color: Theme.danger
                    border.width: 1
                    Text {
                        id: warn
                        anchors.fill: parent
                        anchors.margins: Theme.s8
                        wrapMode: Text.Wrap
                        text: "Unsupported date-format tokens — falling back to YYYY-MM-DD."
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.captionPx
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Today's note: " + page.vm.todayPreview()
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
                ActionButton {
                    text: "Change vault…"
                    onClicked: if (page.app) page.app.goSetup()
                }
            }

            // ---- Carry-over ------------------------------------------------
            Card {
                title: "Carry-over"
                Row {
                    width: parent.width
                    SettingRow { label: "Auto carry-over"; width: parent.width - sw.width }
                    Switch {
                        id: sw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.rolloverEnabled
                        onToggled: page.vm.setRolloverEnabled(checked)
                    }
                }
                SettingRow { label: "Lookback (days): " + page.vm.lookback }
                Slider {
                    id: lb
                    width: parent.width
                    from: 1; to: 90; stepSize: 1
                    value: page.vm.lookback
                    onMoved: page.vm.setLookback(Math.round(value))
                }
                ActionButton {
                    text: "Run carry-over now"
                    onClicked: if (page.app) page.app.runRolloverNow()
                }
            }

            // ---- General ---------------------------------------------------
            Card {
                title: "General"
                Row {
                    width: parent.width
                    SettingRow { label: "Close to tray"; width: parent.width - ctt.width }
                    Switch {
                        id: ctt
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.closeToTray
                        onToggled: page.vm.setCloseToTray(checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow { label: "Start with Windows"; width: parent.width - asw.width }
                    Switch {
                        id: asw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.autostart
                        onToggled: page.vm.setAutostart(checked)
                    }
                }
                Labeled { label: "Global quick-add"; value: page.vm.hotkey }
            }

            // ---- About -----------------------------------------------------
            Card {
                title: "About"
                Text {
                    text: "Dayline " + page.vm.version
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.bodyPx
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Your tasks live in your Obsidian vault as plain Markdown."
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
            }

            Item { height: Theme.s16 }
        }
    }

    Accessible.name: "Settings"
    Accessible.role: Accessible.Pane
}
