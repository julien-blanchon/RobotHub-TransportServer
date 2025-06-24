import enum
import logging
from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============= ENUMS =============


class ParticipantRole(enum.StrEnum):
    """Participant roles in a video room"""

    PRODUCER = "producer"  # Camera/video source
    CONSUMER = "consumer"  # Video viewer/receiver


class MessageType(enum.StrEnum):
    """WebSocket message types for video streaming"""

    # === CONNECTION & LIFECYCLE ===
    JOINED = "joined"  # Confirmation of successful room join
    ERROR = "error"  # Error notifications

    # === CONNECTION HEALTH ===
    HEARTBEAT = "heartbeat"  # Client ping for connection health
    HEARTBEAT_ACK = "heartbeat_ack"  # Server response to heartbeat

    # === VIDEO STREAMING ===
    VIDEO_CONFIG_UPDATE = "video_config_update"  # Video configuration update
    STREAM_STARTED = "stream_started"  # Stream started notification
    STREAM_STOPPED = "stream_stopped"  # Stream stopped notification
    RECOVERY_TRIGGERED = "recovery_triggered"  # Recovery policy triggered
    EMERGENCY_STOP = "emergency_stop"  # Emergency stop command

    # === STATUS & MONITORING ===
    STATUS_UPDATE = "status_update"  # General status updates
    STREAM_STATS = "stream_stats"  # Stream statistics
    PARTICIPANT_JOINED = "participant_joined"  # Participant joined room
    PARTICIPANT_LEFT = "participant_left"  # Participant left room

    # === WEBRTC SIGNALING ===
    WEBRTC_OFFER = "webrtc_offer"  # WebRTC offer forwarded between participants
    WEBRTC_ANSWER = "webrtc_answer"  # WebRTC answer forwarded between participants
    WEBRTC_ICE = "webrtc_ice"  # WebRTC ICE candidate forwarded between participants


class RecoveryPolicy(enum.StrEnum):
    """Frame recovery policies for handling video interruptions"""

    FREEZE_LAST_FRAME = "freeze_last_frame"  # Reuse last valid frame
    CONNECTION_INFO = "connection_info"  # Show informative status frame
    BLACK_SCREEN = "black_screen"  # Black screen with same dimensions
    FADE_TO_BLACK = "fade_to_black"  # Gradually fade last frame to black
    OVERLAY_STATUS = "overlay_status"  # Show last frame with overlay


class VideoEncoding(enum.StrEnum):
    """Supported video encodings"""

    JPEG = "jpeg"
    H264 = "h264"
    VP8 = "vp8"
    VP9 = "vp9"


class RawWebRTCMessageType(enum.StrEnum):
    """Raw WebRTC signaling message types from client API"""

    OFFER = "offer"
    ANSWER = "answer"
    ICE = "ice"


# ============= CORE DATA STRUCTURES (TypedDict) =============


class VideoConfigDict(TypedDict, total=False):
    """Video configuration dictionary"""

    encoding: str | None
    resolution: dict[str, int] | None  # {"width": int, "height": int}
    framerate: int | None
    bitrate: int | None
    quality: int | None


class StreamStatsDict(TypedDict):
    """Stream statistics structure"""

    stream_id: str
    duration_seconds: float
    frame_count: int
    total_bytes: int
    average_fps: float
    average_bitrate: float


class ParticipantInfoDict(TypedDict):
    """Information about room participants"""

    producer: str | None
    consumers: list[str]
    total: int


# ============= WEBRTC DATA STRUCTURES =============


class RTCSessionDescriptionDict(TypedDict):
    """RTCSessionDescription structure"""

    type: Literal["offer", "answer"]
    sdp: str


class RTCIceCandidateDict(TypedDict, total=False):
    """RTCIceCandidate structure (from candidate.toJSON())"""

    candidate: str
    sdpMLineIndex: int | None
    sdpMid: str | None
    usernameFragment: str | None


# ============= BASE MESSAGE STRUCTURES =============


class BaseWebSocketMessage(TypedDict):
    """Base WebSocket message structure"""

    type: str
    timestamp: str | None


# ============= CONNECTION & LIFECYCLE MESSAGES =============


class JoinedMessageDict(BaseWebSocketMessage):
    """Confirmation of successful room join"""

    type: Literal[MessageType.JOINED]
    room_id: str
    role: Literal[ParticipantRole.PRODUCER, ParticipantRole.CONSUMER]


class ErrorMessageDict(BaseWebSocketMessage):
    """Error notification message"""

    type: Literal[MessageType.ERROR]
    message: str
    code: str | None


# ============= CONNECTION HEALTH MESSAGES =============


class HeartbeatMessageDict(BaseWebSocketMessage):
    """Heartbeat ping from client"""

    type: Literal[MessageType.HEARTBEAT]


class HeartbeatAckMessageDict(BaseWebSocketMessage):
    """Heartbeat acknowledgment from server"""

    type: Literal[MessageType.HEARTBEAT_ACK]


# ============= VIDEO STREAMING MESSAGES =============


class VideoConfigUpdateMessageDict(BaseWebSocketMessage):
    """Video configuration update message"""

    type: Literal[MessageType.VIDEO_CONFIG_UPDATE]
    config: VideoConfigDict
    source: str | None


class StreamStartedMessageDict(BaseWebSocketMessage):
    """Stream started notification"""

    type: Literal[MessageType.STREAM_STARTED]
    config: VideoConfigDict
    participant_id: str


class StreamStoppedMessageDict(BaseWebSocketMessage):
    """Stream stopped notification"""

    type: Literal[MessageType.STREAM_STOPPED]
    participant_id: str
    reason: str | None


class RecoveryTriggeredMessageDict(BaseWebSocketMessage):
    """Recovery policy triggered message"""

    type: Literal[MessageType.RECOVERY_TRIGGERED]
    policy: Literal[
        RecoveryPolicy.FREEZE_LAST_FRAME,
        RecoveryPolicy.CONNECTION_INFO,
        RecoveryPolicy.BLACK_SCREEN,
        RecoveryPolicy.FADE_TO_BLACK,
        RecoveryPolicy.OVERLAY_STATUS,
    ]
    reason: str


class EmergencyStopMessageDict(BaseWebSocketMessage):
    """Emergency stop message"""

    type: Literal[MessageType.EMERGENCY_STOP]
    reason: str
    source: str | None


# ============= STATUS & MONITORING MESSAGES =============


class StreamStatsMessageDict(BaseWebSocketMessage):
    """Stream statistics message"""

    type: Literal[MessageType.STREAM_STATS]
    stats: StreamStatsDict


class StatusUpdateMessageDict(BaseWebSocketMessage):
    """General status update message"""

    type: Literal[MessageType.STATUS_UPDATE]
    status: str
    data: dict[str, Any] | None


class ParticipantJoinedMessageDict(BaseWebSocketMessage):
    """Participant joined room notification"""

    type: Literal[MessageType.PARTICIPANT_JOINED]
    room_id: str
    participant_id: str
    role: Literal[ParticipantRole.PRODUCER, ParticipantRole.CONSUMER]


class ParticipantLeftMessageDict(BaseWebSocketMessage):
    """Participant left room notification"""

    type: Literal[MessageType.PARTICIPANT_LEFT]
    room_id: str
    participant_id: str
    role: Literal[ParticipantRole.PRODUCER, ParticipantRole.CONSUMER]


# ============= WEBRTC SIGNALING MESSAGES =============


class WebRTCOfferMessageDict(BaseWebSocketMessage):
    """WebRTC offer message"""

    type: Literal[MessageType.WEBRTC_OFFER]
    offer: RTCSessionDescriptionDict  # RTCSessionDescription
    from_producer: str


class WebRTCAnswerMessageDict(BaseWebSocketMessage):
    """WebRTC answer message"""

    type: Literal[MessageType.WEBRTC_ANSWER]
    answer: RTCSessionDescriptionDict  # RTCSessionDescription
    from_consumer: str


class WebRTCIceMessageDict(BaseWebSocketMessage):
    """WebRTC ICE candidate message"""

    type: Literal[MessageType.WEBRTC_ICE]
    candidate: RTCIceCandidateDict  # RTCIceCandidate
    from_producer: str | None
    from_consumer: str | None


# ============= RAW WEBRTC SIGNALING (from client WebRTC API) =============


class RawWebRTCOfferDict(TypedDict, total=False):
    """Raw WebRTC offer from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.OFFER]
    sdp: str
    target_consumer: str | None  # For producer targeting specific consumer


class RawWebRTCAnswerDict(TypedDict, total=False):
    """Raw WebRTC answer from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.ANSWER]
    sdp: str
    target_producer: str | None  # For consumer responding to specific producer


class RawWebRTCIceDict(TypedDict, total=False):
    """Raw WebRTC ICE candidate from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.ICE]
    candidate: RTCIceCandidateDict
    target_consumer: str | None  # For producer sending to specific consumer
    target_producer: str | None  # For consumer sending to specific producer


# ============= MESSAGE GROUPS (Union Types) =============

# Connection lifecycle messages
ConnectionLifecycleMessage = JoinedMessageDict | ErrorMessageDict

# Connection health messages
ConnectionHealthMessage = HeartbeatMessageDict | HeartbeatAckMessageDict

# Video streaming messages
VideoStreamingMessage = (
    VideoConfigUpdateMessageDict
    | StreamStartedMessageDict
    | StreamStoppedMessageDict
    | RecoveryTriggeredMessageDict
    | EmergencyStopMessageDict
)

# Status and monitoring messages
StatusMonitoringMessage = (
    StreamStatsMessageDict
    | StatusUpdateMessageDict
    | ParticipantJoinedMessageDict
    | ParticipantLeftMessageDict
)

# WebRTC signaling messages (WebSocket forwarding)
WebRTCSignalingMessage = (
    WebRTCOfferMessageDict | WebRTCAnswerMessageDict | WebRTCIceMessageDict
)

# Raw WebRTC signaling messages (from client WebRTC API)
RawWebRTCSignalingMessage = RawWebRTCOfferDict | RawWebRTCAnswerDict | RawWebRTCIceDict

# All WebSocket messages
WebSocketMessageDict = (
    ConnectionLifecycleMessage
    | ConnectionHealthMessage
    | VideoStreamingMessage
    | StatusMonitoringMessage
    | WebRTCSignalingMessage
)

# ============= PYDANTIC MODELS (API INPUT/OUTPUT ONLY) =============


class VideoConfig(BaseModel):
    """Video processing configuration"""

    encoding: VideoEncoding | None = Field(default=VideoEncoding.VP8)
    resolution: dict[str, int] | None = Field(default={"width": 640, "height": 480})
    framerate: int | None = Field(default=30, ge=1, le=120)
    bitrate: int | None = Field(default=1000000, ge=100000)
    quality: int | None = Field(default=80, ge=1, le=100)


class RecoveryConfig(BaseModel):
    """Video frame recovery configuration"""

    frame_timeout_ms: int = Field(default=100, ge=10, le=1000)
    max_frame_reuse_count: int = Field(default=3, ge=1, le=10)
    recovery_policy: RecoveryPolicy = RecoveryPolicy.FREEZE_LAST_FRAME
    fallback_policy: RecoveryPolicy = RecoveryPolicy.CONNECTION_INFO
    show_hold_indicators: bool = True
    info_frame_bg_color: tuple[int, int, int] = (20, 30, 60)
    info_frame_text_color: tuple[int, int, int] = (200, 200, 200)
    fade_intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    overlay_opacity: float = Field(default=0.3, ge=0.0, le=1.0)


class CreateRoomRequest(BaseModel):
    """Request to create a new video room"""

    room_id: str | None = None
    workspace_id: str | None = None  # Optional - will be generated if not provided
    name: str | None = None
    config: VideoConfig | None = None
    recovery_config: RecoveryConfig | None = None
    max_consumers: int = Field(default=10, ge=1, le=100)


class WebRTCSignalRequest(BaseModel):
    """WebRTC signaling request"""

    client_id: str = Field(..., min_length=1, max_length=100)
    message: dict[str, Any]  # Raw WebRTC signaling message


class JoinMessage(BaseModel):
    """Message to join a video room"""

    participant_id: str = Field(..., min_length=1, max_length=100)
    role: ParticipantRole


class ParticipantInfo(BaseModel):
    """Information about room participants"""

    producer: str | None
    consumers: list[str]
    total: int


class StreamStats(BaseModel):
    """Video stream statistics"""

    stream_id: str
    duration_seconds: float
    frame_count: int
    total_bytes: int
    average_fps: float
    average_bitrate: float


class RoomInfo(BaseModel):
    """Basic room information"""

    id: str
    workspace_id: str
    participants: ParticipantInfo
    frame_count: int
    config: VideoConfig
    has_producer: bool
    active_consumers: int


class RoomState(BaseModel):
    """Detailed room state"""

    room_id: str
    workspace_id: str
    participants: ParticipantInfo
    frame_count: int
    last_frame_time: datetime | None
    current_config: VideoConfig
    timestamp: str


# ============= DEPRECATED - KEEPING FOR BACKWARDS COMPATIBILITY =============
# These Pydantic WebSocket models are kept for any remaining references
# but should be migrated to use the TypedDict versions above


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""

    type: MessageType
    timestamp: str | None = None


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


class HeartbeatMessage(WebSocketMessage):
    """Heartbeat ping from client"""

    type: MessageType = MessageType.HEARTBEAT


class HeartbeatAckMessage(WebSocketMessage):
    """Heartbeat acknowledgment from server"""

    type: MessageType = MessageType.HEARTBEAT_ACK


class VideoConfigUpdateMessage(WebSocketMessage):
    """Video configuration update message"""

    type: MessageType = MessageType.VIDEO_CONFIG_UPDATE
    config: VideoConfig
    source: str | None = None


class StreamStartedMessage(WebSocketMessage):
    """Stream started notification"""

    type: MessageType = MessageType.STREAM_STARTED
    config: VideoConfig
    participant_id: str


class StreamStoppedMessage(WebSocketMessage):
    """Stream stopped notification"""

    type: MessageType = MessageType.STREAM_STOPPED
    participant_id: str
    reason: str | None = None


class RecoveryTriggeredMessage(WebSocketMessage):
    """Recovery policy triggered message"""

    type: MessageType = MessageType.RECOVERY_TRIGGERED
    policy: RecoveryPolicy
    reason: str


class EmergencyStopMessage(WebSocketMessage):
    """Emergency stop message"""

    type: MessageType = MessageType.EMERGENCY_STOP
    reason: str
    source: str | None = None


class StreamStatsMessage(WebSocketMessage):
    """Stream statistics message"""

    type: MessageType = MessageType.STREAM_STATS
    stats: StreamStats


class StatusUpdateMessage(WebSocketMessage):
    """General status update message"""

    type: MessageType = MessageType.STATUS_UPDATE
    status: str
    data: dict[str, Any] | None = None


class ParticipantJoinedMessage(WebSocketMessage):
    """Participant joined room notification"""

    type: MessageType = MessageType.PARTICIPANT_JOINED
    room_id: str
    participant_id: str
    role: ParticipantRole


class WebRTCOfferMessage(WebSocketMessage):
    """WebRTC offer message"""

    type: MessageType = MessageType.WEBRTC_OFFER
    offer: RTCSessionDescriptionDict
    from_producer: str


class WebRTCAnswerMessage(WebSocketMessage):
    """WebRTC answer message"""

    type: MessageType = MessageType.WEBRTC_ANSWER
    answer: RTCSessionDescriptionDict
    from_consumer: str


class WebRTCIceMessage(WebSocketMessage):
    """WebRTC ICE candidate message"""

    type: MessageType = MessageType.WEBRTC_ICE
    candidate: RTCIceCandidateDict
    from_producer: str | None = None
    from_consumer: str | None = None


# ============= PYDANTIC MODELS FOR RAW WEBRTC SIGNALING =============


class RawWebRTCOffer(BaseModel):
    """Raw WebRTC offer from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.OFFER]
    sdp: str
    target_consumer: str | None = None  # For producer targeting specific consumer


class RawWebRTCAnswer(BaseModel):
    """Raw WebRTC answer from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.ANSWER]
    sdp: str
    target_producer: str | None = None  # For consumer responding to specific producer


class RawWebRTCIce(BaseModel):
    """Raw WebRTC ICE candidate from client WebRTC API"""

    type: Literal[RawWebRTCMessageType.ICE]
    candidate: RTCIceCandidateDict
    target_consumer: str | None = None  # For producer sending to specific consumer
    target_producer: str | None = None  # For consumer sending to specific producer
