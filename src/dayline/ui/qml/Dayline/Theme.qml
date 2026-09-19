pragma Singleton
import QtQuick

// Single source of design tokens (PRD §4.2). All pages/components bind here.
QtObject {
    id: theme

    /// Set from AppViewModel (Windows apps theme) via Main.qml; tests can override.
    property bool dark: false
    /// Motion kill-switch (§4.2; wired to OS setting in M6).
    property bool animate: true

    // ---- spacing scale -------------------------------------------------
    readonly property int s4: 4
    readonly property int s8: 8
    readonly property int s12: 12
    readonly property int s16: 16
    readonly property int s24: 24
    readonly property int s32: 32

    // ---- radii ----------------------------------------------------------
    readonly property int radiusControl: 8
    readonly property int radiusCard: 12
    readonly property int radiusChip: 999

    // ---- typography -------------------------------------------------------
    readonly property string fontFamily: "Segoe UI Variable Text, Segoe UI"
    readonly property int titlePx: 22
    readonly property int sectionPx: 15
    readonly property int bodyPx: 14
    readonly property int captionPx: 12

    // ---- motion ---------------------------------------------------------
    readonly property int motionMs: 160
    readonly property int ringMotionMs: 250

    // ---- colors -----------------------------------------------------------
    readonly property color bg:            dark ? "#16171A" : "#F7F7F9"
    readonly property color surface:       dark ? "#1F2024" : "#FFFFFF"
    readonly property color surfaceAlt:    dark ? "#26282D" : "#F0F1F5"
    readonly property color border:        dark ? "#2E3036" : "#E4E4EA"
    readonly property color text:          dark ? "#ECECF1" : "#1B1B1F"
    readonly property color textSecondary: dark ? "#A0A3AB" : "#5F6368"
    readonly property color accent:        dark ? "#7C93FF" : "#4F6BED"
    readonly property color onAccent:      dark ? "#16171A" : "#FFFFFF"
    readonly property color success:       dark ? "#4CC38A" : "#2E9E6B"
    readonly property color danger:        dark ? "#F0736F" : "#D64545"

    readonly property color prioHigh:  dark ? "#EF5350" : "#D32F2F"
    readonly property color prioMed:   dark ? "#FFB74D" : "#F57C00"
    readonly property color prioLow:   dark ? "#64B5F6" : "#1976D2"
    readonly property color prioNone:  dark ? "#6B6E76" : "#9E9E9E"

    function prioColor(p) {
        switch (p) {
        case "high": return prioHigh
        case "medium": return prioMed
        case "low": return prioLow
        default: return prioNone
        }
    }

    // elevation: 1 px border + very soft shadow
    readonly property real cardShadowOpacity: 0.06
    readonly property int cardShadowRadius: 12
    readonly property int cardShadowDy: 2
}
