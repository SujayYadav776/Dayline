import QtQuick
import QtQuick.Controls
import Dayline

// Application shell (paper design): textured background, bookmark-ribbon
// header with day navigation, page routing, the bottom calendar strip, and
// the pull-up Progress panel. Shortcuts + quick-add are preserved.
ApplicationWindow {
    id: win
    objectName: "rootWindow"
    property bool qmlReady: false
    property bool progressOpen: false
    property bool drawerOpen: false

    visible: typeof StartHidden === "undefined" ? true : !StartHidden
    flags: Qt.Window | Qt.FramelessWindowHint
    width: 360
    height: 600
    minimumWidth: 320
    minimumHeight: 460
    title: "Dayline"
    // Thin paper drops the opaque fill so the Mica backdrop shows through the
    // 92% paper layer below; otherwise the window paints solid paper.
    color: App.thinPaper && App.micaActive ? "transparent" : Theme.bg

    // Theme singleton follows the VM's dark flag live (OS watch in M5).
    Binding {
        target: Theme
        property: "dark"
        value: App.dark
        restoreMode: Binding.RestoreNone
    }

    // Panel mode: dismiss like the notification centre when focus is lost.
    onActiveChanged: {
        if (!active && win.visible && App.vaultReady && App.autoHide)
            win.hide()
    }
    Binding {
        target: Theme
        property: "animate"
        value: !App.reduceMotion
        restoreMode: Binding.RestoreNone
    }

    // The window deliberately does NOT restore its last size/position:
    // app.py anchors it bottom-right at startup, at the default small size.
    Component.onCompleted: win.qmlReady = true

    // Close-to-tray (FR-P2): hide instead of quit when the setting is on.
    onClosing: (mouse) => {
        if (typeof Controller !== "undefined" && Controller && Controller.suppressClose())
            mouse.accepted = false
    }

    // ---- paper background ---------------------------------------------------
    // Thin paper: the window colour goes transparent and a 92% paper layer
    // sits under the grain, letting the Win11 Mica blur peek through.
    Rectangle {
        anchors.fill: parent
        color: Theme.bg
        opacity: 0.92
        visible: App.thinPaper && App.micaActive
        z: -3
    }
    Image {
        anchors.fill: parent
        source: "../assets/paper.png"
        fillMode: Image.Tile
        opacity: Theme.dark ? 0.06 : 0.6
        z: -2
    }

    // ---- custom title bar (macOS traffic lights) -----------------------------
    TitleBar {
        id: titleBar
        win: win
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        z: 23                                   // above the staggered menu (z 22)
    }

    // red bookmark ribbon with the menu (hamburger) — touches the top border
    // and floats above the title strip (z 25) so its click area stays live.
    Item {
        id: ribbon
        objectName: "ribbonMenu"
        x: 15
        y: -10                                  // artwork has 10 px shadow padding on top
        width: 66
        height: 124
        z: 25
        visible: App.vaultReady
        Image {
            anchors.fill: parent
            source: "../assets/ribbon.png"
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Column {
            id: burger
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 76
            spacing: 5
            Repeater {
                model: 3
                Rectangle { width: 20; height: 2.5; radius: 1; color: Theme.accentInk }
            }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: win.drawerOpen = !win.drawerOpen
        }
        Accessible.role: Accessible.Button
        Accessible.name: "Menu"
    }

    // ---- header (day nav + profile) ------------------------------------------
    Item {
        id: header
        objectName: "header"
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 64
        z: 10
        visible: App.vaultReady

        // center: ‹ TODAY ›
        Row {
            id: dayNav
            objectName: "dayNav"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 12
            spacing: Theme.s24

            Component {
                id: navChevron
                Item {
                    property bool back: true
                    width: 20
                    height: 28
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        anchors.centerIn: parent
                        text: back ? "‹" : "›"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 20
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: back ? App.prevDay() : App.nextDay()
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: back ? "Previous day" : "Next day"
                }
            }
            Loader {
                sourceComponent: navChevron
                onLoaded: item.back = true
            }

            Text {
                id: navTitle
                objectName: "navTitle"
                anchors.verticalCenter: parent.verticalCenter
                text: App.page === "today" ? "TODAY"
                    : App.page === "week" ? "WEEK" : "SETTINGS"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.navPx
                font.weight: Theme.weightLabel
                font.letterSpacing: Theme.navTracking
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: App.goToday()
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Back to today"
            }

            Loader {
                sourceComponent: navChevron
                onLoaded: item.back = false
            }
        }

        // right: profile glyph → Settings
        Item {
            id: personIcon
            objectName: "profileButton"
            anchors.right: parent.right
            anchors.rightMargin: Theme.s24
            anchors.verticalCenter: dayNav.verticalCenter
            width: 24
            height: 24
            Image {
                anchors.fill: parent
                source: "../assets/person.png"
                smooth: true
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: App.setPage("settings")
            }
            Accessible.role: Accessible.Button
            Accessible.name: "Settings"
        }
    }

    // ---- content area (pages + progress overlay) ------------------------------
    Item {
        id: contentArea
        anchors.top: header.bottom
        anchors.bottom: strip.top
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        visible: App.vaultReady

        Loader {
            id: pageLoader
            objectName: "pageLoader"
            anchors.fill: parent
            sourceComponent: pageCompFor(App.page)
        }

        ProgressPanel {
            id: progressPanel
            anchors.fill: parent
            vm: App.weekVM
            today: App.todayVM
            open: win.progressOpen && App.page === "today"
        }
    }

    // ---- move-to-day menu (replaces the old drag gesture) ---------------------
    function openMoveMenu(taskKey, taskText) {
        moveMenu.open(taskKey, taskText, App.weekVM.strip)
    }
    MouseArea {
        anchors.fill: parent
        z: 39
        visible: moveMenu.opacity > 0.01
        onClicked: moveMenu.close()
    }
    MoveDayMenu {
        id: moveMenu
        objectName: "moveMenu"
        z: 40
        width: parent.width - 2 * Theme.s16
        anchors.horizontalCenter: parent.horizontalCenter
        y: titleBar.height + Theme.s8
    }

    // ---- bottom calendar strip -------------------------------------------------
    WeekStrip {
        id: strip
        objectName: "stripFooter"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: App.vaultReady
        vm: App.weekVM
        progressOpen: win.progressOpen
        onDayPicked: (dateStr) => App.selectDay(dateStr)
        onProgressToggled: {
            App.setPage("today")
            win.progressOpen = !win.progressOpen
        }
    }

    // ---- staggered menu (bookmark ribbon) -------------------------------------
    // React Bits <StaggeredMenu /> port (D-033): bookmark-red pre-layers sweep
    // in, the paper panel trails them, then the uppercase numbered rows rise
    // out of their clip line with a 10° tilt. Full-width panel (the original's
    // ≤1024px behaviour), so it sits under the ribbon + title bar which stay
    // clickable as the always-available close controls (Escape also works).
    StaggeredMenu {
        id: menu
        objectName: "staggeredMenu"
        anchors.fill: parent
        z: 22
        opened: win.drawerOpen
        items: [
            {"id": "today", "label": "Today"},
            {"id": "week", "label": "Week"},
            {"id": "settings", "label": "Settings"},
            {"id": "quit", "label": "Quit"}
        ]
        onDismiss: win.drawerOpen = false
        onItemChosen: (id) => {
            if (id === "quit") { Qt.quit(); return }
            App.setPage(id)
            win.drawerOpen = false
        }
    }

    // setup / onboarding when no vault is ready
    Loader {
        anchors.fill: parent
        anchors.margins: Theme.s16
        anchors.topMargin: titleBar.height + Theme.s16
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
        color: "transparent"
        title: "Quick add"
        x: win.x + (win.width - width) / 2
        y: win.y + win.height / 3

        onVisibleChanged: if (visible) qaField.forceActiveFocus()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 6
            radius: 24
            color: Theme.surface
            border.color: Theme.border
            border.width: 1
        }

        function parsedPriority() {
            var m = /(!{1,3})$/.exec(qaField.text.trim())
            if (!m) return ""
            return { 1: "low", 2: "medium", 3: "high" }[m[1].length] || ""
        }

        Row {
            anchors.fill: parent
            anchors.margins: Theme.s16 + 6
            spacing: Theme.s12
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

    // ---- frameless resize edges (native system resize) ------------------------
    Item {
        anchors.fill: parent
        z: 30
        enabled: win.visibility !== Window.Maximized

        MouseArea { x: 0; y: 16; width: 5; height: parent.height - 32
            cursorShape: Qt.SizeHorCursor
            onPressed: win.startSystemResize(Qt.LeftEdge) }
        MouseArea { anchors.right: parent.right; y: 16; width: 5; height: parent.height - 32
            cursorShape: Qt.SizeHorCursor
            onPressed: win.startSystemResize(Qt.RightEdge) }
        MouseArea { x: 16; anchors.bottom: parent.bottom; width: parent.width - 32; height: 5
            cursorShape: Qt.SizeVerCursor
            onPressed: win.startSystemResize(Qt.BottomEdge) }
        MouseArea { x: 14; y: 0; width: parent.width - 112; height: 4
            cursorShape: Qt.SizeVerCursor
            onPressed: win.startSystemResize(Qt.TopEdge) }
        MouseArea { x: 0; y: 0; width: 14; height: 14
            cursorShape: Qt.SizeFDiagCursor
            onPressed: win.startSystemResize(Qt.LeftEdge | Qt.TopEdge) }
        MouseArea { anchors.right: parent.right; y: 0; width: 14; height: 14
            cursorShape: Qt.SizeBDiagCursor
            onPressed: win.startSystemResize(Qt.RightEdge | Qt.TopEdge) }
        MouseArea { x: 0; anchors.bottom: parent.bottom; width: 14; height: 14
            cursorShape: Qt.SizeBDiagCursor
            onPressed: win.startSystemResize(Qt.LeftEdge | Qt.BottomEdge) }
        MouseArea { anchors.right: parent.right; anchors.bottom: parent.bottom; width: 14; height: 14
            cursorShape: Qt.SizeFDiagCursor
            onPressed: win.startSystemResize(Qt.RightEdge | Qt.BottomEdge) }
    }

    // ---- keyboard (§4.6) ------------------------------------------------------
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
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (win.drawerOpen) win.drawerOpen = false
            else if (win.progressOpen) win.progressOpen = false
        }
    }
}
