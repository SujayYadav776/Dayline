import QtQuick

// Loading skeleton bar (§4.5, ≤ 300 ms shimmer-free).
Rectangle {
    width: parent ? parent.width : 0
    height: 18
    radius: 6
    color: Theme.surfaceAlt
    opacity: 0.7
}
