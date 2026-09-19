import QtQuick
import QtQuick.Controls
import Dayline

// Application shell: window state, theme sync, page routing, shortcuts.
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

    // Theme singleton follows the VM's dark flag live (§4.2 wiring; OS watch in M5).
    Binding {
        target: Theme
        property: "dark"
        value: App.dark
        restoreMode: Binding.RestoreNone
    }

    Component.onCompleted: win.qmlReady = true

    // ---- routing -----------------------------------------------------------
    Loader {
        id: pageLoader
        anchors.fill: parent
        anchors.margins: Theme.s16
        sourceComponent: App.vaultReady ? todayPageComp : setupComp
    }

    Component {
        id: todayPageComp
        TodayPage { vm: App.todayVM }
    }
    Component {
        id: setupComp
        VaultSetupView { app: App }
    }

    // ---- keyboard (§4.6; day navigation live in M2) --------------------------
    Shortcut {
        sequence: "Alt+Right"
        onActivated: App.nextDay()
    }
    Shortcut {
        sequence: "Alt+Left"
        onActivated: App.prevDay()
    }
    Shortcut {
        sequence: "Ctrl+T"
        onActivated: App.goToday()
    }
    Shortcut {
        sequence: "Ctrl+R"
        onActivated: App.retry()
    }
    Shortcut {
        sequence: "Ctrl+N"
        onActivated: if (pageLoader.item && pageLoader.item.focusAdd) pageLoader.item.focusAdd()
    }
    Shortcut {
        sequence: "Ctrl+Z"
        onActivated: App.undo()
    }
    Shortcut {
        sequence: "Ctrl+Shift+Z"
        onActivated: App.redo()
    }
    Shortcut {
        sequence: "Ctrl+Y"
        onActivated: App.redo()
    }
}
