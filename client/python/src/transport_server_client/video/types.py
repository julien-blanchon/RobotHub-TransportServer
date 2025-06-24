"""
Type definitions for LeRobot Arena Video Client
Fully synchronized with server-side models and JavaScript client
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Union

# ============= CORE TYPES =============


class ParticipantRole(Enum):
    PRODUCER = "producer"
    CONSUMER = "consumer"


class MessageType(Enum):
    FRAME_UPDATE = "frame_update"
    VIDEO_CONFIG_UPDATE = "video_config_update"
    STREAM_STARTED = "stream_started"
    STREAM_STOPPED = "stream_stopped"
    RECOVERY_TRIGGERED = "recovery_triggered"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    EMERGENCY_STOP = "emergency_stop"
    JOINED = "joined"
    ERROR = "error"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    WEBRTC_OFFER = "webrtc_offer"
    WEBRTC_ANSWER = "webrtc_answer"
    WEBRTC_ICE = "webrtc_ice"
    STATUS_UPDATE = "status_update"
    STREAM_STATS = "stream_stats"


# ============= VIDEO CONFIGURATION =============


@dataclass
class Resolution:
    width: int
    height: int


class VideoEncoding(Enum):
    JPEG = "jpeg"
    H264 = "h264"
    VP8 = "vp8"
    VP9 = "vp9"


class RecoveryPolicy(Enum):
    FREEZE_LAST_FRAME = "freeze_last_frame"
    CONNECTION_INFO = "connection_info"
    BLACK_SCREEN = "black_screen"
    FADE_TO_BLACK = "fade_to_black"
    OVERLAY_STATUS = "overlay_status"


@dataclass
class VideoConfig:
    encoding: VideoEncoding | None = None
    resolution: Resolution | None = None
    framerate: int | None = None
    bitrate: int | None = None
    quality: int | None = None


@dataclass
class RecoveryConfig:
    frame_timeout_ms: int | None = None
    max_frame_reuse_count: int | None = None
    recovery_policy: RecoveryPolicy | None = None
    fallback_policy: RecoveryPolicy | None = None
    show_hold_indicators: bool | None = None
    info_frame_bg_color: list[int] | None = None
    info_frame_text_color: list[int] | None = None
    fade_intensity: float | None = None
    overlay_opacity: float | None = None


# ============= DATA STRUCTURES =============


@dataclass
class FrameData:
    data: bytes
    metadata: dict[str, Any] | None = None


@dataclass
class StreamStats:
    stream_id: str
    duration_seconds: float
    frame_count: int
    total_bytes: int
    average_fps: float
    average_bitrate: float


@dataclass
class ParticipantInfo:
    producer: str | None
    consumers: list[str]
    total: int


@dataclass
class RoomInfo:
    id: str
    workspace_id: str
    participants: ParticipantInfo
    frame_count: int
    config: VideoConfig
    has_producer: bool
    active_consumers: int


@dataclass
class RoomState:
    room_id: str
    workspace_id: str
    participants: ParticipantInfo
    frame_count: int
    last_frame_time: str | None
    current_config: VideoConfig
    timestamp: str


@dataclass
class ConnectionInfo:
    connected: bool
    workspace_id: str | None
    room_id: str | None
    role: ParticipantRole | None
    participant_id: str | None
    base_url: str


# ============= MESSAGE TYPES =============


@dataclass
class BaseMessage:
    type: MessageType
    timestamp: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class FrameUpdateMessage(BaseMessage):
    data: bytes = b""
    metadata: dict[str, Any] | None = None


@dataclass
class VideoConfigUpdateMessage(BaseMessage):
    config: VideoConfig | None = None
    source: str | None = None


@dataclass
class StreamStartedMessage(BaseMessage):
    config: VideoConfig | None = None
    participant_id: str = ""


@dataclass
class StreamStoppedMessage(BaseMessage):
    participant_id: str = ""
    reason: str | None = None


@dataclass
class RecoveryTriggeredMessage(BaseMessage):
    policy: RecoveryPolicy = RecoveryPolicy.FREEZE_LAST_FRAME
    reason: str = ""


@dataclass
class EmergencyStopMessage(BaseMessage):
    reason: str = ""
    source: str | None = None


@dataclass
class JoinedMessage(BaseMessage):
    room_id: str = ""
    role: ParticipantRole = ParticipantRole.CONSUMER


@dataclass
class ErrorMessage(BaseMessage):
    message: str = ""
    code: str | None = None


@dataclass
class ParticipantJoinedMessage(BaseMessage):
    room_id: str = ""
    participant_id: str = ""
    role: ParticipantRole = ParticipantRole.CONSUMER


@dataclass
class ParticipantLeftMessage(BaseMessage):
    room_id: str = ""
    participant_id: str = ""
    role: ParticipantRole = ParticipantRole.CONSUMER


@dataclass
class WebRTCOfferMessage(BaseMessage):
    offer: dict[str, Any] | None = None
    from_producer: str = ""


@dataclass
class WebRTCAnswerMessage(BaseMessage):
    answer: dict[str, Any] | None = None
    from_consumer: str = ""


@dataclass
class WebRTCIceMessage(BaseMessage):
    candidate: dict[str, Any] | None = None
    from_producer: str | None = None
    from_consumer: str | None = None


@dataclass
class StatusUpdateMessage(BaseMessage):
    status: str = ""
    data: dict[str, Any] | None = None


@dataclass
class StreamStatsMessage(BaseMessage):
    stats: StreamStats | None = None


# Union type for all WebSocket messages
WebSocketMessage = Union[
    FrameUpdateMessage,
    VideoConfigUpdateMessage,
    StreamStartedMessage,
    StreamStoppedMessage,
    RecoveryTriggeredMessage,
    EmergencyStopMessage,
    JoinedMessage,
    ErrorMessage,
    ParticipantJoinedMessage,
    ParticipantLeftMessage,
    WebRTCOfferMessage,
    WebRTCAnswerMessage,
    WebRTCIceMessage,
    StatusUpdateMessage,
    StreamStatsMessage,
]


# ============= API RESPONSE TYPES =============


@dataclass
class ApiResponse:
    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None


@dataclass
class ListRoomsResponse:
    success: bool
    workspace_id: str
    rooms: list[RoomInfo]
    total: int


@dataclass
class CreateRoomResponse:
    success: bool
    workspace_id: str
    room_id: str
    message: str


@dataclass
class GetRoomResponse:
    success: bool
    workspace_id: str
    room: RoomInfo


@dataclass
class GetRoomStateResponse:
    success: bool
    workspace_id: str
    state: RoomState


@dataclass
class DeleteRoomResponse:
    success: bool
    workspace_id: str
    message: str


@dataclass
class WebRTCSignalResponse:
    success: bool
    workspace_id: str
    response: dict[str, Any] | None = None
    message: str | None = None


# ============= REQUEST TYPES =============


@dataclass
class CreateRoomRequest:
    room_id: str | None = None
    workspace_id: str | None = None
    name: str | None = None
    config: VideoConfig | None = None
    recovery_config: RecoveryConfig | None = None
    max_consumers: int | None = None


@dataclass
class WebRTCSignalRequest:
    client_id: str
    message: dict[str, Any]


@dataclass
class JoinMessage:
    participant_id: str
    role: ParticipantRole


# ============= WEBRTC TYPES =============


@dataclass
class WebRTCConfig:
    ice_servers: list[dict[str, Any]] | None = None
    constraints: dict[str, Any] | None = None
    bitrate: int | None = None
    framerate: int | None = None
    resolution: Resolution | None = None
    codec_preferences: list[str] | None = None


@dataclass
class WebRTCStats:
    video_bits_per_second: float
    frames_per_second: float
    frame_width: int
    frame_height: int
    packets_lost: int
    total_packets: int


# ============= EVENT CALLBACK TYPES =============

FrameUpdateCallback = Callable[[FrameData], None]
VideoConfigUpdateCallback = Callable[[VideoConfig], None]
StreamStartedCallback = Callable[[VideoConfig, str], None]
StreamStoppedCallback = Callable[[str, str | None], None]
RecoveryTriggeredCallback = Callable[[RecoveryPolicy, str], None]
StatusUpdateCallback = Callable[[str, dict[str, Any] | None], None]
StreamStatsCallback = Callable[[StreamStats], None]
ErrorCallback = Callable[[str], None]
ConnectedCallback = Callable[[], None]
DisconnectedCallback = Callable[[], None]


# ============= CLIENT OPTIONS =============


@dataclass
class ClientOptions:
    base_url: str | None = None
    timeout: float | None = None
    reconnect_attempts: int | None = None
    heartbeat_interval: float | None = None
    webrtc_config: WebRTCConfig | None = None


# ============= DEFAULTS =============

DEFAULT_RESOLUTION = Resolution(width=640, height=480)
DEFAULT_VIDEO_CONFIG = VideoConfig(
    resolution=DEFAULT_RESOLUTION,
    framerate=30,
    bitrate=1000000,
    encoding=VideoEncoding.VP8,
)
DEFAULT_CLIENT_OPTIONS = ClientOptions(
    timeout=5.0, reconnect_attempts=3, heartbeat_interval=30.0
)
