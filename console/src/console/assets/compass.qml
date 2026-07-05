pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    required property var rover
    property real bearing: 0.0 //temporary value for testing, should be rover.bearing

    width: 240
    height: 240
    antialiasing: true
    color: palette.window

    Rectangle {
        id: bezelRing
        width: (parent.width > parent.height) ? parent.height : parent.width
        height: width
        anchors.centerIn: parent
        radius: width / 2
        color: (palette.window.hsvValue > 0.5) ? "#1f1f1f" : "white"
        border.color: (palette.window.hsvValue > 0.5) ? "#555555" : "#95a5a6"
        border.width: 10

        Item {
            id: rotatingDial
            anchors.fill: parent
            anchors.margins: parent.border.width

            rotation: -root.bearing

            Behavior on rotation {
                RotationAnimation {
                    direction: RotationAnimation.Shortest
                    duration: 150
                    easing.type: Easing.OutQuad
                }
            }

            //Tick Marks & Labels
            Repeater {
                model: 36
                delegate: Item {
                    id: tickContainer

                    required property int index

                    anchors.fill: parent
                    rotation: index * 10

                    Rectangle {
                        width: (tickContainer.index % 9 === 0) ? 4 : 2
                        height: bezelRing.width * 0.07
                        color: (tickContainer.index % 9 === 0) ? "#e74c3c" : "#cccccc"
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: bezelRing.width * 0.02
                    }

                    Text {
                        text: {
                            if (tickContainer.index === 0)
                            return "N";
                            if (tickContainer.index === 9)
                            return "E";
                            if (tickContainer.index === 18)
                            return "S";
                            if (tickContainer.index === 27)
                            return "W";
                            return "";
                        }
                        color: (palette.window.hsvValue > 0.5) ? "#dddddd" : "#333333"
                        font.pixelSize: (tickContainer.index % 9 === 0) ? bezelRing.width * 0.1 : bezelRing.width * 0.07
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: bezelRing.width * 0.1
                        rotation: -tickContainer.rotation
                    }
                }
            }
        }

        // === THE FIXED INDICATOR ===
        Shape {
            id: pointer
            width: bezelRing.width * 0.09
            height: bezelRing.width * 0.09
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.border.width + bezelRing.width * 0.04
            z: 10
            ShapePath {
                strokeWidth: 0
                strokeColor: "black"
                fillColor: "#cccccc"
                startX: pointer.width / 2
                startY: 0
                PathLine {
                    x: 0
                    y: pointer.height
                }
                PathLine {
                    x: pointer.width
                    y: pointer.height
                }
                PathLine {
                    x: pointer.width / 2
                    y: 0
                }
            }
        }

        // === Center Heading Readout ===
        Rectangle {
            anchors.centerIn: parent
            width: bezelRing.width * 0.4
            height: bezelRing.width * 0.2
            radius: bezelRing.width * 0.05
            color: "#cc000000"

            Text {
                anchors.centerIn: parent
                // BINDING: Update text readout from Python property
                text: root.bearing.toFixed(0) + "°"
                color: "white"
                font.pixelSize: bezelRing.width * 0.1
                font.bold: true
            }
        }
    }
}
