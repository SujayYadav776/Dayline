pragma Singleton
import QtQuick

// Single source of design tokens (PRD §4.2). All pages/components bind here.
QtObject {
    id: theme

    /// Wired to the Windows apps-theme setting in M5 (FR-P9); fixed light for M0.
    readonly property bool dark: false

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
    readonly property int titleLinePx: 28
    readonly property int sectionPx: 15
    readonly property int sectionLinePx: 20
    readonly property int bodyPx: 14
    readonly property int bodyLinePx: 20
    readonly property int captionPx: 12
    readonly property int captionLinePx: 16

    // ---- motion ---------------------------------------------------------
    readonly property int motionMs: 160          // 120–200 ms ease-out
    readonly property int ringMotionMs: 250      // progress ring ≤ 250 ms

    // ---- colors -----------------------------------------------------------
    readonly property color bg:            dark ? "#16171A" : "#F7F7F9"
    readonly property color surface:       dark ? "#1F2024" : "#FFFFFF"
    readonly property color surfaceAlt:    dark ? "#26282D" : "#F0F1F5"
    readonly property color border:        dark ? "#2E3036" : "#E4E4EA"
    readonly property color text:          dark ? "#ECECF1" : "#1B1B1F"
    readonly property color textSecondary: dark ? "#A0A3AB" : "#5F6368"
    readonly property color accent:        dark ? "#7C93FF" : "#4F6BED"
    readonly property color success:       dark ? "#4CC38A" : "#2E9E6B"
    readonly property color danger:        dark ? "#F0736F" : "#D64545"

    readonly property color prioHigh:  dark ? "#EF5350" : "#D32F2F"
    readonly property color prioMed:   dark ? "#FFB74D" : "#F57C00"
    readonly property color prioLow:   dark ? "#64B5F6" : "#1976D2"
    readonly property color prioNone:  dark ? "#6B6E76" : "#9E9E9E"

    // elevation: 1 px border + very soft shadow
    readonly property real cardShadowOpacity: 0.06
    readonly property int cardShadowRadius: 12
    readonly property int cardShadowDy: 2
}
