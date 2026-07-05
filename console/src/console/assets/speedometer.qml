pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root
    width: 200
    height: 200
    color: palette.window

    property int maxSpeed: 12
    required property var rover
    property real speed: 1 //temporary value for testing, should be rover.speed

    Rectangle {
        id: container
        width: root.width > root.height ? root.height : root.width
        height: width
        radius: width / 2
        anchors.centerIn: parent
        color: "black"
        border.width: 6
        border.color: (palette.window.hsvValue > 0.5) ? "#444444" : "#555555"

        antialiasing: true

        Repeater {
            model: root.maxSpeed * 2 + 1
            delegate: Item {
                id: tickContainer
                required property int index
                anchors.margins: container.border.width + container.width * 0.05
                anchors.fill: parent
                rotation: 225 + (270 / (root.maxSpeed*2)) * index

                Rectangle {
                    id: tick
                    width: (parent.index % 4 === 0) ? 2 : 1
                    height: (parent.index % 4 === 0) ? container.width * 0.08 : container.width * 0.05
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: "#cccccc"
                }
                Text {
                    id: tickLabel
                    anchors.top: tick.bottom
                    anchors.topMargin: container.width * 0.02
                    anchors.horizontalCenter: parent.horizontalCenter
                    rotation: -parent.rotation
                    text: parent.index / 2
                    color: "#cccccc"
                    font.pixelSize: container.width * 0.08
                    font.bold: true
                    visible: (parent.index % 4 === 0)? true : false
                }
            }
        }
        Item {
            id:needleContainer
            anchors.margins: container.border.width + container.width * 0.05
            anchors.fill: parent
            rotation: 225 + (270 / root.maxSpeed) * root.speed
            Rectangle {
                id: needleBase
                width: container.width * 0.05
                height: width
                radius: width / 2
                anchors.centerIn: parent
                color: "red"
            }
            Shape {
                id: needle
                anchors.bottom: needleBase.verticalCenter
                anchors.horizontalCenter: needleBase.horizontalCenter
                width: container.width * 0.035
                height: parent.height * 0.475
                ShapePath {
                    strokeWidth: 0
                    fillColor: "red"
                    startX: needle.width / 2
                    startY: 0
                    PathLine {
                        x: needle.width
                        y: needle.height
                    }
                    PathLine {
                        x: 0
                        y: needle.height
                    }
                    PathLine {
                        x: needle.width / 2
                        y: 0
                    }
                }
            }
        }
    }
}