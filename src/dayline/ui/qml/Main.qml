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
    color: Theme.bg

    // Theme singleton follows the VM's dark flag live (OS watch in M5).
    Binding {
        target: Theme
        property: "dark"
        value: App.dark
        restoreMode: Binding.RestoreNone
    }

    Component.onCompleted: win.qmlReady = true

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
        sourceComponent: VaultSetupView { app: App }
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
