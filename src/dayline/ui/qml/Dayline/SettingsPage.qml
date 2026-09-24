import QtQuick
import QtQuick.Controls
import Dayline

// Settings (PRD §3.7): grouped cards, all changes apply live. shadcn styling.
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
            y: Theme.ribbonOverhang
            width: page.width - 2 * Theme.s24
            spacing: Theme.s16

            Text {
                text: "Settings"
                font.family: Theme.serifFamily
                font.pixelSize: Theme.titlePx + 2
                font.weight: Theme.weightHeading
                color: Theme.text
            }

            // ---- Appearance ------------------------------------------------
            Card {
                title: "Appearance"
                SettingRow { label: "Theme" }
                Select {
                    width: parent.width
                    model: ["system", "light", "dark"]
                    currentIndex: ["system", "light", "dark"].indexOf(page.vm.theme)
                    onActivated: page.vm.setTheme(currentText)
                }
                SettingRow { label: "Sort tasks by" }
                Select {
                    width: parent.width
                    model: ["priority", "manual"]
                    currentIndex: page.vm.sortMode === "manual" ? 1 : 0
                    onActivated: page.vm.setSortMode(currentText)
                }
                SettingRow { label: "Week starts on" }
                Select {
                    width: parent.width
                    model: ["Monday", "Sunday"]
                    currentIndex: page.vm.weekStart === "sun" ? 1 : 0
                    onActivated: page.vm.setWeekStart(currentText === "Sunday" ? "sun" : "mon")
                }
                Row {
                    width: parent.width
                    visible: page.app && page.app.micaSupported
                    SettingRow { label: "Mica backdrop"; width: parent.width - micw.width }
                    Toggle {
                        id: micw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.mica
                        onToggled: page.vm.setMica(!checked)
                    }
                }
                Row {
                    width: parent.width
                    visible: page.app && page.app.micaSupported
                    SettingRow {
                        label: "Thin paper (translucent)"; width: parent.width - tpw.width
                    }
                    Toggle {
                        id: tpw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.thinPaper
                        onToggled: page.vm.setThinPaper(!checked)
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
                    color: Qt.alpha(Theme.danger, Theme.dark ? 0.16 : 0.08)
                    border.color: Qt.alpha(Theme.danger, 0.4)
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
                    Toggle {
                        id: sw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.rolloverEnabled
                        onToggled: page.vm.setRolloverEnabled(!checked)
                    }
                }
                SettingRow { label: "Lookback (days): " + page.vm.lookback }
                Slider {
                    id: lb
                    width: parent.width
                    from: 1; to: 90; stepSize: 1
                    value: page.vm.lookback
                    onMoved: page.vm.setLookback(Math.round(value))
                    implicitHeight: 20
                    background: Rectangle {
                        x: lb.leftPadding
                        y: lb.topPadding + lb.availableHeight / 2 - height / 2
                        width: lb.availableWidth
                        height: 6
                        radius: 3
                        color: Theme.surfaceAlt
                        Rectangle {
                            width: lb.visualPosition * parent.width
                            height: parent.height
                            radius: 3
                            color: Theme.accent
                        }
                    }
                    handle: Rectangle {
                        x: lb.leftPadding + lb.visualPosition * (lb.availableWidth - width)
                        y: lb.topPadding + lb.availableHeight / 2 - height / 2
                        width: 18; height: 18; radius: 9
                        color: Theme.surface
                        border.color: Theme.accent
                        border.width: 2
                    }
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
                    SettingRow { label: "Start hidden in tray"; width: parent.width - sh.width }
                    Toggle {
                        id: sh
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.startHidden
                        onToggled: page.vm.setStartHidden(!checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow { label: "Close to tray"; width: parent.width - ctt.width }
                    Toggle {
                        id: ctt
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.closeToTray
                        onToggled: page.vm.setCloseToTray(!checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow {
                        label: "Auto-hide when unfocused"; width: parent.width - ah.width
                    }
                    Toggle {
                        id: ah
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.autoHide
                        onToggled: page.vm.setAutoHide(!checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow { label: "Daily due reminder (9:00)"; width: parent.width - dr.width }
                    Toggle {
                        id: dr
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.dueReminders
                        onToggled: page.vm.setDueReminders(!checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow { label: "Completion sound"; width: parent.width - csd.width }
                    Toggle {
                        id: csd
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.completionSound
                        onToggled: page.vm.setCompletionSound(!checked)
                    }
                }
                Row {
                    width: parent.width
                    SettingRow { label: "Start with Windows"; width: parent.width - asw.width }
                    Toggle {
                        id: asw
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.autostart
                        onToggled: page.vm.setAutostart(!checked)
                    }
                }
                Labeled { label: "Global quick-add"; value: page.vm.hotkey }
            }

            // ---- Updates ---------------------------------------------------
            Card {
                title: "Updates"
                Row {
                    width: parent.width
                    SettingRow { label: "Auto-check (daily)"; width: parent.width - uc.width }
                    Toggle {
                        id: uc
                        anchors.verticalCenter: parent.verticalCenter
                        checked: page.vm.updateCheckEnabled
                        onToggled: page.vm.setUpdateCheckEnabled(!checked)
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Dayline v" + (page.app ? page.app.currentVersion : "")
                          + "  ·  updates are checked only when you opt in"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
                ActionButton {
                    text: page.app && page.app.updateChecking ? "Checking…" : "Check now"
                    enabled: !(page.app && page.app.updateChecking)
                    onClicked: if (page.app) page.app.checkForUpdates()
                }
                Text {
                    visible: page.app && page.app.updateStatus !== ""
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: page.app ? page.app.updateStatus : ""
                    color: page.app && page.app.updateAvailable ? Theme.success : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.captionPx
                }
                Row {
                    visible: page.app && page.app.updateAvailable
                    spacing: Theme.s8
                    ActionButton {
                        variant: "default"
                        text: "Install update"
                        onClicked: if (page.app) page.app.installUpdate()
                    }
                    ActionButton {
                        text: "Release notes"
                        onClicked: if (page.app && page.app.updatePageUrl)
                                       Qt.openUrlExternally(page.app.updatePageUrl)
                    }
                }
            }

            // ---- About -----------------------------------------------------
            Card {
                title: "About"
                Row {
                    spacing: Theme.s12
                    Image {
                        source: "../../assets/app.png"
                        sourceSize.width: 40
                        sourceSize.height: 40
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Dayline " + page.vm.version
                        color: Theme.text
                        font.family: Theme.serifFamily
                        font.pixelSize: Theme.bodyPx + 2
                        font.weight: Theme.weightHeading
                    }
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
