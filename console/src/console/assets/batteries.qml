pragma ComponentBehavior: Bound
import QtQuick
import Qt5Compat.GraphicalEffects

Rectangle {
    id: root
    width: 200
    height: 150
    color: palette.window

    required property var rover

    Repeater {
        model: 2
        delegate: Item {
            required property int index
            id: batteryContainer
            
            // Logic: Select battery by index, normalize 0-24V to 0.0-1.0
            property real rawVoltage: (index === 0) ? rover.battery_1 : rover.battery_2
            property real normalizedLevel: Math.max(0.0, Math.min(1.0, rawVoltage / 24.0))

            anchors.margins: 10
            anchors.left: root.left
            anchors.right: root.right
            anchors.top: index === 0 ? root.top : root.verticalCenter
            anchors.bottom: index === 0 ? root.verticalCenter : root.bottom

            Item {
                id: batteryShape
                anchors.fill: parent

                Rectangle {
                    id: batteryLevelRect
                    width: (batteryBody.width - 4) * normalizedLevel
                    height: batteryBody.height - 4
                    anchors.left: batteryBody.left
                    anchors.verticalCenter: batteryBody.verticalCenter
                    anchors.margins: 2
                    
                    color: {
                        if (normalizedLevel > 0.5) return "green"
                        else if (normalizedLevel > 0.2) return "#f4d03f"
                        else return "red"
                    }

                    layer.enabled: true
                    layer.effect: OpacityMask {
                        maskSource: mask
                    }

                    Rectangle {
                        id: mask
                        width: batteryBody.width
                        height: batteryBody.height
                        radius: batteryBody.radius
                        border.width: batteryBody.border.width
                        border.color: "transparent"
                        color: "black"
                        visible: false
                    }
                }

                Rectangle {
                    id: batteryBody
                    width: parent.width * 0.95
                    height: parent.height
                    radius: 4
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    color: "transparent"
                    border.color: (palette.window.hsvValue > 0.5) ? "#1f1f1f" : "#cccccc"
                    border.width: 2
                }

                Rectangle {
                    id: batteryTip
                    width: parent.width * 0.05
                    height: parent.height * 0.6
                    radius: 4
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    color: (palette.window.hsvValue > 0.5) ? "#1f1f1f" : "#cccccc"
                    
                    Rectangle {
                        id: tipPadding
                        width: parent.width * 0.5
                        height: parent.height
                        anchors.left: parent.left
                        anchors.leftMargin: -1
                        anchors.verticalCenter: parent.verticalCenter
                        color: parent.color
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                color: (palette.window.hsvValue > 0.5) ? "#1f1f1f" : "#cccccc"
                text: (normalizedLevel * 100).toFixed(0) + "% (" + rawVoltage.toFixed(1) + "V)"
                font.pixelSize: Math.min(parent.height * 0.4, 22)
                font.bold: true
            }
        }
    }
}