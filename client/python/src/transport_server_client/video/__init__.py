"""
LeRobot Arena Video Client - Main Module

TypeScript/JavaScript client for video streaming and monitoring
"""

# Export core classes
from .consumer import VideoConsumer
from .core import VideoClientCore

# Export factory functions for convenience
from .factory import create_client, create_consumer_client, create_producer_client
from .producer import CameraVideoTrack, CustomVideoTrack, VideoProducer

# Export all types
from .types import (
    DEFAULT_CLIENT_OPTIONS,
    # Defaults
    DEFAULT_RESOLUTION,
    DEFAULT_VIDEO_CONFIG,
    # API response types
    ApiResponse,
    # Message types
    BaseMessage,
    # Client options
    ClientOptions,
    ConnectedCallback,
    ConnectionInfo,
    # Request types
    CreateRoomRequest,
    CreateRoomResponse,
    DeleteRoomResponse,
    DisconnectedCallback,
    EmergencyStopMessage,
    ErrorCallback,
    ErrorMessage,
    # Data structures
    FrameData,
    # Event callback types
    FrameUpdateCallback,
    FrameUpdateMessage,
    GetRoomResponse,
    GetRoomStateResponse,
    JoinedMessage,
    JoinMessage,
    ListRoomsResponse,
    MessageType,
    ParticipantInfo,
    ParticipantJoinedMessage,
    ParticipantLeftMessage,
    # Core types
    ParticipantRole,
    RecoveryConfig,
    RecoveryPolicy,
    RecoveryTriggeredCallback,
    RecoveryTriggeredMessage,
    # Configuration types
    Resolution,
    RoomInfo,
    RoomState,
    StatusUpdateCallback,
    StatusUpdateMessage,
    StreamStartedCallback,
    StreamStartedMessage,
    StreamStats,
    StreamStatsCallback,
    StreamStatsMessage,
    StreamStoppedCallback,
    StreamStoppedMessage,
    VideoConfig,
    VideoConfigUpdateCallback,
    VideoConfigUpdateMessage,
    VideoEncoding,
    WebRTCAnswerMessage,
    # WebRTC types
    WebRTCConfig,
    WebRTCIceMessage,
    WebRTCOfferMessage,
    WebRTCSignalRequest,
    WebRTCSignalResponse,
    WebRTCStats,
)

__all__ = [
    "DEFAULT_CLIENT_OPTIONS",
    # Defaults
    "DEFAULT_RESOLUTION",
    "DEFAULT_VIDEO_CONFIG",
    # API response types
    "ApiResponse",
    # Message types
    "BaseMessage",
    "CameraVideoTrack",
    # Client options
    "ClientOptions",
    "ConnectedCallback",
    "ConnectionInfo",
    # Request types
    "CreateRoomRequest",
    "CreateRoomResponse",
    "CustomVideoTrack",
    "DeleteRoomResponse",
    "DisconnectedCallback",
    "EmergencyStopMessage",
    "ErrorCallback",
    "ErrorMessage",
    # Data structures
    "FrameData",
    # Event callback types
    "FrameUpdateCallback",
    "FrameUpdateMessage",
    "GetRoomResponse",
    "GetRoomStateResponse",
    "JoinMessage",
    "JoinedMessage",
    "ListRoomsResponse",
    "MessageType",
    "ParticipantInfo",
    "ParticipantJoinedMessage",
    "ParticipantLeftMessage",
    # Core types
    "ParticipantRole",
    "RecoveryConfig",
    "RecoveryPolicy",
    "RecoveryTriggeredCallback",
    "RecoveryTriggeredMessage",
    # Configuration types
    "Resolution",
    "RoomInfo",
    "RoomState",
    "StatusUpdateCallback",
    "StatusUpdateMessage",
    "StreamStartedCallback",
    "StreamStartedMessage",
    "StreamStats",
    "StreamStatsCallback",
    "StreamStatsMessage",
    "StreamStoppedCallback",
    "StreamStoppedMessage",
    # Core classes
    "VideoClientCore",
    "VideoConfig",
    "VideoConfigUpdateCallback",
    "VideoConfigUpdateMessage",
    "VideoConsumer",
    "VideoEncoding",
    "VideoProducer",
    "WebRTCAnswerMessage",
    # WebRTC types
    "WebRTCConfig",
    "WebRTCIceMessage",
    "WebRTCOfferMessage",
    "WebRTCSignalRequest",
    "WebRTCSignalResponse",
    "WebRTCStats",
    "create_client",
    "create_consumer_client",
    # Factory functions
    "create_producer_client",
]
