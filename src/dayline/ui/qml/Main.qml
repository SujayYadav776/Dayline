import QtQuick
import QtQuick.Controls
import Dayline

// Application shell: window state, theme sync, page routing, footer nav, shortcuts.
ApplicationWindow {
    id: win
    objectName: "rootWindow"
    property bool qmlReady: false

    visible: true
    width: 440
    height: 720
    minimumWidth: 360
    minimumHeight: 480
    title: "Dayline"
    // Mica backdrop: tint the window near-opaque but slightly translucent when
    // active so the OS-composited blur shows through the page gaps; cards stay solid.
    readonly property color windowTint:
        App.micaActive ? Qt.rgba(Theme.bg.r, Theme.bg.g, Theme.bg.b, 0.80) : Theme.bg
    color: windowTint

    // Theme singleton follows the VM's dark flag live (OS watch in M5).
    Binding {
        target: Theme
        property: "dark"
        value: App.dark
        restoreMode: Binding.RestoreNone
    }
    Binding {
        target: Theme
        property: "animate"
        value: !App.reduceMotion
        restoreMode: Binding.RestoreNone
    }

    // Restore remembered size/position (PRD §4.3).
    Component.onCompleted: {
        win.qmlReady = true
        var g = App.geometry
        if (g && g.width > 0) {
            win.width = g.width
            win.height = g.height
            if (g.x !== undefined) win.x = g.x
            if (g.y !== undefined) win.y = g.y
        }
    }

    // Close-to-tray (FR-P2): hide instead of quit when the setting is on.
    onClosing: (mouse) => {
        App.saveGeometry(win.x, win.y, win.width, win.height)
        if (typeof Controller !== "undefined" && Controller && Controller.suppressClose())
            mouse.accepted = false
    }

    // ---- routing -----------------------------------------------------------
    Column {
        anchors.fill: parent
        visible: App.vaultReady

        Loader {
            id: pageLoader
            width: parent.width
            height: parent.height - footer.height
            sourceComponent: pageCompFor(App.page)
        }

        // footer navigation
        Rectangle {
            id: footer
            width: parent.width
            height: 52
            color: Theme.surface
            border.color: Theme.border
            Row {
                anchors.fill: parent
                Repeater {
                    model: [
                        {"id": "today", "label": "Today", "key": "1"},
                        {"id": "week", "label": "Week", "key": "2"},
                        {"id": "settings", "label": "Settings", "key": "3"}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: footer.width / 3
                        height: footer.height
                        color: App.page === modelData.id ? Theme.surfaceAlt : "transparent"
                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label
                                color: App.page === modelData.id ? Theme.accent : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.captionPx
                                font.weight: App.page === modelData.id ? Font.DemiBold : Font.Normal
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: App.setPage(modelData.id)
                        }
                        Accessible.role: Accessible.TabButton
                        Accessible.name: modelData.label
                    }
                }
            }
        }
    }

    // setup / onboarding when no vault is ready
    Loader {
        anchors.fill: parent
        anchors.margins: Theme.s16
        visible: !App.vaultReady
        active: !App.vaultReady
        sourceComponent: App.firstRun ? onboardingComp : setupComp
    }

    Component {
        id: onboardingComp
        Onboarding { app: App }
    }
    Component {
        id: setupComp
        VaultSetupView { app: App }
    }

    function pageCompFor(name) {
        if (name === "week") return weekComp
        if (name === "settings") return settingsComp
        return todayComp
    }
    Component {
        id: todayComp
        TodayPage { vm: App.todayVM }
    }
    Component {
        id: weekComp
        WeekPage { vm: App.weekVM }
    }
    Component {
        id: settingsComp
        SettingsPage { vm: App.settingsVM; app: App }
    }

    // ---- quick-add popup (FR-P6) --------------------------------------------
    Window {
        id: quickAdd
        width: 480
        height: 76
        visible: App.quickAddVisible
        flags: Qt.Dialog | Qt.FramelessWindowHint
        color: Theme.surface
        title: "Quick add"
        x: win.x + (win.width - width) / 2
        y: win.y + win.height / 3

        onVisibleChanged: if (visible) qaField.forceActiveFocus()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Theme.radiusCard
            color: Theme.surface
            border.color: Theme.accent
            border.width: 1
        }

        function parsedPriority() {
            var m = /(!{1,3})$/.exec(qaField.text.trim())
            if (!m) return ""
            return { 1: "low", 2: "medium", 3: "high" }[m[1].length] || ""
        }

        Row {
            anchors.fill: parent
            anchors.margins: Theme.s16
            spacing: Theme.s8
            Rectangle {
                width: 10; height: 10; radius: 5
                anchors.verticalCenter: parent.verticalCenter
                visible: quickAdd.parsedPriority() !== ""
                color: Theme.prioColor(quickAdd.parsedPriority())
            }
            TextInput {
                id: qaField
                width: parent.width - 10 - parent.spacing - 60
                anchors.verticalCenter: parent.verticalCenter
                font.family: Theme.fontFamily
                font.pixelSize: Theme.bodyPx
                color: Theme.text
                selectionColor: Theme.accent
                cursorVisible: true
                clip: true
                text: ""
                function submit() {
                    var t = text.trim()
                    if (t.length > 0) App.addTask(t)
                    text = ""
                    App.hideQuickAdd()
                }
                Keys.onReturnPressed: submit()
                Keys.onEnterPressed: submit()
                Keys.onEscapePressed: App.hideQuickAdd()
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Enter ↵"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.captionPx
            }
        }
    }

    // ---- keyboard (§4.6) ----------------------------------------------------
    Shortcut { sequence: "Alt+Right"; onActivated: App.nextDay() }
    Shortcut { sequence: "Alt+Left"; onActivated: App.prevDay() }
    Shortcut { sequence: "Ctrl+T"; onActivated: App.goToday() }
    Shortcut { sequence: "Ctrl+R"; onActivated: App.retry() }
    Shortcut { sequence: "Ctrl+1"; onActivated: App.setPage("today") }
    Shortcut { sequence: "Ctrl+2"; onActivated: App.setPage("week") }
    Shortcut { sequence: "Ctrl+3"; onActivated: App.setPage("settings") }
    Shortcut {
        sequence: "Ctrl+N"
        onActivated: if (pageLoader.item && pageLoader.item.focusAdd) pageLoader.item.focusAdd()
    }
    Shortcut { sequence: "Ctrl+Z"; onActivated: App.undo() }
    Shortcut { sequence: "Ctrl+Shift+Z"; onActivated: App.redo() }
    Shortcut { sequence: "Ctrl+Y"; onActivated: App.redo() }
}
