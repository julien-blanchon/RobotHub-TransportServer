import logging
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============= ENUMS =============


class ParticipantRole(str, Enum):
    """Participant roles in a robotics room"""

    PRODUCER = "producer"  # Controller/master
    CONSUMER = "consumer"  # Robot/visualizer


class MessageType(str, Enum):
    """WebSocket message types organized by category"""

    # === CONNECTION & LIFECYCLE ===
    JOINED = "joined"  # Confirmation of successful room join
    ERROR = "error"  # Error notifications

    # === CONNECTION HEALTH ===
    HEARTBEAT = "heartbeat"  # Client ping for connection health
    HEARTBEAT_ACK = "heartbeat_ack"  # Server response to heartbeat

    # === ROBOT CONTROL (Core) ===
    JOINT_UPDATE = "joint_update"  # Producer → Consumers: Joint position commands
    STATE_SYNC = "state_sync"  # Server → Consumer: Initial state synchronization

    # === EMERGENCY & SAFETY ===
    EMERGENCY_STOP = "emergency_stop"  # Emergency stop command (any direction)

    # === STATUS & MONITORING ===
    STATUS_UPDATE = "status_update"  # General status updates
    CONSUMER_STATUS = "consumer_status"  # Specific consumer status reports


class RobotType(str, Enum):
    """Supported robot types"""

    SO_ARM_100 = "so-arm100"
    GENERIC = "generic"


# ============= CORE MODELS =============


class CreateRoomRequest(BaseModel):
    """Request to create a new robotics room"""

    room_id: str | None = None
    workspace_id: str | None = None  # Optional - will be generated if not provided
    name: str | None = None
    robot_type: RobotType = RobotType.SO_ARM_100
    max_consumers: int = Field(default=10, ge=1, le=100)


class JointUpdate(BaseModel):
    """Single joint position update"""

    name: str = Field(..., min_length=1, max_length=50)
    value: float = Field(..., ge=-360.0, le=360.0)  # Degrees
    speed: float | None = Field(None, ge=0.0, le=100.0)  # Percentage


class JointCommand(BaseModel):
    """Command containing multiple joint updates"""

    joints: list[JointUpdate] = Field(..., min_length=1, max_length=20)


class EmergencyStop(BaseModel):
    """Emergency stop command"""

    enabled: bool = True


# ============= RESPONSE MODELS =============


class ParticipantInfo(BaseModel):
    """Information about room participants"""

    producer: str | None
    consumers: list[str]
    total: int


class RoomInfo(BaseModel):
    """Basic room information"""

    id: str
    workspace_id: str
    participants: ParticipantInfo
    joints_count: int
    has_producer: bool
    active_consumers: int


class RoomState(BaseModel):
    """Detailed room state"""

    room_id: str
    workspace_id: str
    joints: dict[str, float]
    participants: ParticipantInfo
    timestamp: str


# ============= WEBSOCKET MODELS =============


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""

    type: MessageType
    timestamp: str | None = None


class JoinMessage(BaseModel):
    """Message to join a room"""

    participant_id: str = Field(..., min_length=1, max_length=100)
    role: ParticipantRole


# === CONNECTION & LIFECYCLE MESSAGES ===


class JoinedMessage(WebSocketMessage):
    """Confirmation of successful room join"""

    type: MessageType = MessageType.JOINED
    room_id: str
    role: ParticipantRole


class ErrorMessage(WebSocketMessage):
    """Error notification message"""

    type: MessageType = MessageType.ERROR
    message: str
    code: str | None = None


# === CONNECTION HEALTH MESSAGES ===


class HeartbeatMessage(WebSocketMessage):
    """Heartbeat ping from client"""

    type: MessageType = MessageType.HEARTBEAT


class HeartbeatAckMessage(WebSocketMessage):
    """Heartbeat acknowledgment from server"""

    type: MessageType = MessageType.HEARTBEAT_ACK


# === ROBOT CONTROL MESSAGES ===


class JointUpdateMessage(WebSocketMessage):
    """Joint position update command (Producer → Consumers)"""

    type: MessageType = MessageType.JOINT_UPDATE
    data: list[JointUpdate]
    source: str | None = None  # "api" or participant_id


class StateSyncMessage(WebSocketMessage):
    """Initial state synchronization (Server → Consumer)"""

    type: MessageType = MessageType.STATE_SYNC
    data: dict[str, float]  # Current joint positions


# === EMERGENCY & SAFETY MESSAGES ===


class EmergencyStopMessage(WebSocketMessage):
    """Emergency stop command"""

    type: MessageType = MessageType.EMERGENCY_STOP
    enabled: bool = True
    reason: str | None = None


# === STATUS & MONITORING MESSAGES ===


class StatusUpdateMessage(WebSocketMessage):
    """General status update"""

    type: MessageType = MessageType.STATUS_UPDATE
    status: str
    data: dict | None = None


class ConsumerStatusMessage(WebSocketMessage):
    """Consumer-specific status report"""

    type: MessageType = MessageType.CONSUMER_STATUS
    consumer_id: str
    status: str  # "ready", "busy", "error", "offline"
    joint_states: list[dict] | None = None
