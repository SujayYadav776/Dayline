pragma Singleton
import QtQuick

// Single source of design tokens (PRD §4.2). All pages/components bind here.
// Visual language is the "paper" design system ported from the reference
// mockups: warm paper-textured background, red bookmark accent, Varela Round
// body type, Courier New for the typewriter headings, Wallpoet for the big
// pixel date, white rounded cards with soft shadows over the grain.
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

    // ---- radii (cards are generously rounded; controls modest) ----------
    readonly property int radiusControl: 8
    readonly property int radiusCard: 16
    readonly property int radiusChip: 8

    // ---- focus ring ------------------------------------------------------
    readonly property int ringWidth: 2
    readonly property int ringOffset: 2

    // ---- typography -------------------------------------------------------
    readonly property string fontFamily: "Varela Round, Segoe UI"
    readonly property string serifFamily: "Courier New"     // typewriter headings
    readonly property string pixelFamily: "Wallpoet"        // big date digits
    // LEMON MILK (bundled LEMONMILK-Regular.otf) — staggered nav menu labels
    readonly property string menuFamily: "LEMON MILK"
    readonly property int titlePx: 20
    readonly property int sectionPx: 15
    readonly property int bodyPx: 15
    readonly property int captionPx: 12
    readonly property int dayPx: 19        // "saturday"
    readonly property int datePx: 88       // pixel "20"
    readonly property int monthPx: 19      // "september"
    readonly property int navPx: 15        // "TODAY"
    readonly property real titleTracking: 0
    readonly property real headingTracking: 0
    readonly property real navTracking: 2.5
    readonly property int weightLabel: Font.DemiBold
    readonly property int weightHeading: Font.Bold

    // ---- motion ---------------------------------------------------------
    readonly property int motionMs: 150
    readonly property int ringMotionMs: 250
    readonly property int panelMotionMs: 260

    // SpringCheck completion choreography (ported from React Bits — D-032):
    // one spring scalar drives fill swell, box overshoot, tick draw, word dim
    // and the strike-through wipe (which lags behind the fill).
    readonly property real doneOpacity: 0.42   // ink kept by checked words
    readonly property real strikeLag: 0.12     // where on the spring the rule starts
    readonly property real ruleEnd: 0.84       // where the rule wipe finishes
    readonly property real boxSwell: 0.35      // box scale overshoot on the bounce

    // The bookmark ribbon hangs below the header into the content area; pages
    // with left-aligned top content add this clearance so titles don't collide.
    readonly property int ribbonOverhang: 16

    // ---- colors (paper palette) ------------------------------------------
    readonly property color bg:            dark ? "#1B1A17" : "#EDECE9"
    readonly property color surface:       dark ? "#26251F" : "#FFFFFF"   // card
    readonly property color surfaceAlt:    dark ? "#2E2C27" : "#F5F4F1"   // muted fill
    readonly property color border:        dark ? "#383630" : "#E4E2DD"
    readonly property color input:         dark ? "#47443D" : "#D9D7D2"
    readonly property color text:          dark ? "#EFEDE8" : "#212121"   // foreground
    readonly property color textSecondary: dark ? "#A3A099" : "#6C6C6C"
    readonly property color accent:        dark ? "#E86A50" : "#E14A35"   // bookmark red
    readonly property color accentHover:   dark ? "#D0553C" : "#C93F2D"
    // NOT named onAccent — QML parses onXxx: members as signal handlers, so
    // such a property silently resolves to undefined at read sites.
    readonly property color accentInk:      Qt.rgba(1, 1, 1, 1)
    readonly property color ring:          dark ? "#EFEDE8" : "#212121"
    readonly property color heatCell:      dark ? "#34322C" : "#F0F0F0"   // empty activity cell
    readonly property color stripFill:     dark ? "#4B4841" : "#D9D9D9"   // today-column progress
    readonly property color success:       dark ? "#5BB98B" : "#2F855A"
    readonly property color danger:        dark ? "#E4695A" : "#C0392B"
    // dim layer behind modal surfaces (staggered menu, move-to-day backdrop)
    readonly property color scrim:         dark ? "#88000000" : "#66000000"

    readonly property color prioHigh:  dark ? "#F87171" : "#DC2626"
    readonly property color prioMed:   dark ? "#FBBF24" : "#D97706"
    readonly property color prioLow:   dark ? "#60A5FA" : "#2563EB"
    readonly property color prioNone:  dark ? "#8B8880" : "#B9B6B0"

    function prioColor(p) {
        switch (p) {
        case "high": return prioHigh
        case "medium": return prioMed
        case "low": return prioLow
        default: return prioNone
        }
    }

    // activity heat-map levels (0 = no tasks / nothing done → paper gray)
    readonly property var heatLevels: dark
        ? ["#34322C", "#7F4132", "#A54E36", "#C95C3F", "#E86A50"]
        : ["#F0F0F0", "#F8CFC5", "#F2A893", "#E97A5C", "#E14A35"]
    function heatColor(level) {
        var i = Math.max(0, Math.min(4, level | 0))
        return heatLevels[i]
    }

    // elevation: soft drop shadow under white cards
    readonly property real cardShadowOpacity: dark ? 0.4 : 0.12
    readonly property int cardShadowRadius: 14
    readonly property int cardShadowDy: 3
}
