from enum import IntEnum, auto

class PacketType(IntEnum):
    IMU      = auto()
    GPS      = auto()
    ENCODERS = auto()
    ANTENNA = auto()
    STATUS   = auto()
    READY    = auto()
    CMD_VEL  = auto()
    SERVO    = auto()
    LASER    = auto()
    MODE     = auto()
    ACK      = auto()

PAYLOAD_FMT = { # Incoming msgs
    PacketType.IMU:      '<10f',   # q1 q2 q3 q4  α β ψ  ẋ ẏ ż
    PacketType.GPS:      '<11f',   # lon lat cov[9]
    PacketType.ENCODERS: '<4f',    # FL BL FR BR
    PacketType.STATUS:   '<9f',    # bat1 bat2 cur[4] srv1 srv2 flags
    PacketType.ANTENNA:  '<2f',    # lon lat
}