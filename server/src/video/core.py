import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from fractions import Fraction
from functools import lru_cache

import av
import cv2
import numpy as np
from aiortc import (
    RTCConfiguration,
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)
from fastapi import WebSocket, WebSocketDisconnect

from .models import (
    EmergencyStopMessageDict,
    ErrorMessageDict,
    HeartbeatAckMessageDict,
    JoinedMessageDict,
    MessageType,
    ParticipantJoinedMessageDict,
    ParticipantRole,
    RawWebRTCMessageType,
    RawWebRTCSignalingMessage,
    RecoveryConfig,
    RecoveryPolicy,
    RecoveryTriggeredMessageDict,
    StatusUpdateMessageDict,
    StreamStartedMessageDict,
    StreamStatsMessageDict,
    StreamStoppedMessageDict,
    VideoConfig,
    # Core data structures
    VideoConfigUpdateMessageDict,
    WebRTCAnswerMessageDict,
    WebRTCIceMessageDict,
    WebRTCOfferMessageDict,
    WebSocketMessageDict,
)

logger = logging.getLogger(__name__)

# ============= FRAME CACHE (from old code) =============


@lru_cache(maxsize=8)  # Cache up to 8 different resolutions
def get_black_frame(width: int, height: int) -> np.ndarray:
    """Get cached black frame for given dimensions"""
    return np.zeros((height, width, 3), dtype=np.uint8)


@lru_cache(maxsize=4)  # Cache up to 4 different info frame variants
def get_connection_info_frame(
    width: int,
    height: int,
    bg_color: tuple[int, int, int],
    text_color: tuple[int, int, int],
) -> np.ndarray:
    """Get cached connection info frame"""
    frame = np.full((height, width, 3), bg_color, dtype=np.uint8)

    # Add status text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = min(width / 640, height / 480) * 1.2  # Scale with resolution
    thickness = max(1, int(font_scale))

    # Main status message
    text = "RECONNECTING..."
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = height // 2
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, text_color, thickness)

    # Subtitle
    subtitle = "Video stream interrupted"
    subtitle_scale = font_scale * 0.5
    subtitle_size = cv2.getTextSize(subtitle, font, subtitle_scale, 1)[0]
    subtitle_x = (width - subtitle_size[0]) // 2
    subtitle_y = text_y + int(40 * font_scale)
    cv2.putText(
        frame,
        subtitle,
        (subtitle_x, subtitle_y),
        font,
        subtitle_scale,
        text_color,
        1,
    )

    return frame


def add_frame_hold_indicator(frame: np.ndarray, reuse_count: int) -> np.ndarray:
    """Add a subtle indicator that this frame is being held (from old code)"""
    height, width = frame.shape[:2]

    # Create a small colored indicator in top-right corner
    indicator_size = max(6, min(width, height) // 80)  # Scale with frame size
    colors = [
        (255, 200, 0),
        (255, 150, 0),
        (255, 100, 0),
        (255, 50, 0),
    ]  # Yellow to red
    color = colors[min(reuse_count - 1, len(colors) - 1)]

    # Add the indicator
    y_start = 10
    y_end = y_start + indicator_size
    x_start = width - 20
    x_end = x_start + indicator_size

    if y_end < height and x_end < width:
        frame[y_start:y_end, x_start:x_end] = color

    return frame


# ============= VIDEO FRAME TRACK (from old transport.py) =============


class VideoFrameTrack(VideoStreamTrack):
    """Video track for WebRTC (simplified from old VideoStreamTrack)"""

    def __init__(self, recovery_config: RecoveryConfig | None = None):
        super().__init__()
        self.frame_queue = asyncio.Queue(maxsize=2)  # Small buffer for low latency
        self.pts = 0
        self.time_base = 1 / 30  # 30 FPS

        # Frame recovery system (from old code)
        self.config = recovery_config or RecoveryConfig()
        self.last_good_frame = None
        self.last_good_frame_time = 0
        self.frame_reuse_count = 0
        self.last_frame_dimensions = (480, 640)  # Default fallback dimensions

        logger.info(
            f"VideoFrameTrack created with recovery policy: {self.config.recovery_policy.value}"
        )

    async def recv(self) -> av.VideoFrame:
        """Get next video frame for WebRTC transmission with smart recovery (from old code)"""
        current_time = time.time() * 1000  # Convert to milliseconds

        try:
            # Try to get a fresh frame with timeout
            frame_data = await asyncio.wait_for(self.frame_queue.get(), timeout=0.1)

            if frame_data:
                # Decode JPEG to numpy array
                nparr = np.frombuffer(frame_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    # Convert BGR to RGB for WebRTC
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    # Store as last good frame for recovery
                    self.last_good_frame = img_rgb.copy()
                    self.last_good_frame_time = current_time
                    self.last_frame_dimensions = (
                        img_rgb.shape[0],
                        img_rgb.shape[1],
                    )
                    self.frame_reuse_count = 0

                    # Create video frame
                    frame = av.VideoFrame.from_ndarray(img_rgb, format="rgb24")
                else:
                    # JPEG decode failed - use recovery
                    frame = self._create_recovery_frame(current_time)
            else:
                # No frame data - use recovery
                frame = self._create_recovery_frame(current_time)

        except TimeoutError:
            # Timeout waiting for frame - use smart recovery
            frame = self._create_recovery_frame(current_time)

        # Set timing
        frame.pts = self.pts
        frame.time_base = Fraction(1, 30)
        self.pts += 1

        return frame

    def _create_recovery_frame(self, current_time: float):
        """Create a recovery frame using the configured policy (from old code)"""
        # Determine which policy to use
        time_since_last_good = (
            current_time - self.last_good_frame_time
            if self.last_good_frame is not None
            else float("inf")
        )

        if (
            self.last_good_frame is not None
            and time_since_last_good < self.config.frame_timeout_ms
            and self.frame_reuse_count < self.config.max_frame_reuse_count
        ):
            # Use primary recovery policy
            policy = self.config.recovery_policy
            self.frame_reuse_count += 1
        else:
            # Use fallback policy
            policy = self.config.fallback_policy

        # Generate frame based on policy
        recovery_frame = self._apply_recovery_policy(policy)
        frame = av.VideoFrame.from_ndarray(recovery_frame, format="rgb24")
        frame.pts = self.pts
        frame.time_base = Fraction(1, 30)
        return frame

    def _apply_recovery_policy(self, policy: RecoveryPolicy) -> np.ndarray:
        """Apply the specified recovery policy (from old code)"""
        height, width = self.last_frame_dimensions

        if policy == RecoveryPolicy.FREEZE_LAST_FRAME:
            if self.last_good_frame is not None:
                frame = self.last_good_frame.copy()
                if self.config.show_hold_indicators:
                    frame = add_frame_hold_indicator(frame, self.frame_reuse_count)
                return frame
            return get_black_frame(width, height)

        if policy == RecoveryPolicy.CONNECTION_INFO:
            return get_connection_info_frame(
                width,
                height,
                self.config.info_frame_bg_color,
                self.config.info_frame_text_color,
            )

        if policy == RecoveryPolicy.BLACK_SCREEN:
            return get_black_frame(width, height)

        if policy == RecoveryPolicy.FADE_TO_BLACK:
            if self.last_good_frame is not None:
                frame = self.last_good_frame.copy()
                # Apply fade effect
                fade_factor = max(
                    0.0,
                    1.0
                    - (
                        self.frame_reuse_count
                        * self.config.fade_intensity
                        / self.config.max_frame_reuse_count
                    ),
                )
                frame = (frame * fade_factor).astype(np.uint8)
                return frame
            return get_black_frame(width, height)

        if policy == RecoveryPolicy.OVERLAY_STATUS:
            if self.last_good_frame is not None:
                frame = self.last_good_frame.copy()

                # Create overlay
                overlay = np.full_like(
                    frame, self.config.info_frame_bg_color, dtype=np.uint8
                )

                # Add text to overlay
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = min(width / 640, height / 480) * 0.8
                text = "RECONNECTING"
                text_size = cv2.getTextSize(text, font, font_scale, 2)[0]
                text_x = (width - text_size[0]) // 2
                text_y = height // 2
                cv2.putText(
                    overlay,
                    text,
                    (text_x, text_y),
                    font,
                    font_scale,
                    self.config.info_frame_text_color,
                    2,
                )

                # Blend overlay with original frame
                alpha = self.config.overlay_opacity
                frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
                return frame
            return get_black_frame(width, height)

        # Unknown policy, fallback to black
        logger.error(f"Unknown recovery policy: {policy}")
        return get_black_frame(width, height)

    def add_frame(self, frame_data: bytes) -> None:
        """Add frame to queue (non-blocking)"""
        try:
            self.frame_queue.put_nowait(frame_data)
        except asyncio.QueueFull:
            # Drop oldest frame for low latency
            try:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(frame_data)
                logger.debug("Dropped old frame to maintain low latency")
            except asyncio.QueueEmpty:
                pass


# ============= WEBRTC CONNECTION (from old transport.py) =============


class WebRTCConnection:
    """WebRTC connection handling both producers and consumers (from old code)"""

    def __init__(
        self,
        client_id: str,
        room_id: str,
        on_frame_callback: Callable,
        video_core: "VideoCore",
    ):
        self.client_id = client_id
        self.room_id = room_id
        self.on_frame = on_frame_callback
        self.video_core = video_core  # Reference to core for broadcasting
        self.pc = None  # RTCPeerConnection
        self.video_track: VideoFrameTrack | None = None
        self.is_producer = False
        self.is_consumer = False
        self.background_tasks: set[asyncio.Task] = set()

    async def initialize(self):
        """Initialize peer connection (from old code)"""
        config = RTCConfiguration(
            iceServers=[
                RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
            ]
        )
        self.pc = RTCPeerConnection(configuration=config)

        # Set up event handlers
        self.pc.on("track", self._on_track)
        self.pc.on("connectionstatechange", self._on_connection_state)
        self.pc.on("iceconnectionstatechange", self._on_ice_state)

        logger.info(f"WebRTC connection {self.client_id} initialized")

    def _on_connection_state(self) -> None:
        logger.info(
            f"WebRTC {self.client_id} connection state: {self.pc.connectionState}"
        )

    def _on_ice_state(self) -> None:
        logger.info(f"WebRTC {self.client_id} ICE state: {self.pc.iceConnectionState}")

    def _on_track(self, track: av.VideoStream) -> None:
        """Handle incoming video track from producer (from old code)"""
        logger.info(f"WebRTC {self.client_id} received track: {track.kind}")

        if track.kind == "video" or track.type == "video":
            self.is_producer = True
            logger.info(f"WebRTC {self.client_id} is now a PRODUCER")

            # Process incoming video frames
            self._add_background_task(self._process_incoming_video(track))

    async def _process_incoming_video(self, track):
        """Process video frames from producer (from old code)"""
        frame_count = 0

        try:
            while True:
                frame = await track.recv()
                frame_count += 1

                # Convert to OpenCV format
                img = frame.to_ndarray(format="rgb24")
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                # Encode as JPEG
                success, jpeg_data = cv2.imencode(
                    ".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80]
                )

                if success:
                    # Send to processing pipeline
                    await self.on_frame(self.client_id, jpeg_data.tobytes())

                    # Broadcast frames to consumers
                    if self.video_core:
                        await self.video_core.broadcast_to_consumers(
                            self.room_id, jpeg_data.tobytes()
                        )

                    if frame_count % 30 == 0:  # Log every second
                        logger.info(
                            f"WebRTC {self.client_id} processed {frame_count} frames"
                        )

        except Exception:
            logger.exception(f"Error processing video track {self.client_id}")

    async def handle_offer(self, sdp: str, participant_role: str | None = None) -> str:
        """Handle WebRTC offer and determine if producer or consumer (from old code)"""
        try:
            logger.debug(
                f"Processing offer for {self.client_id}, SDP length: {len(sdp)}"
            )

            offer = RTCSessionDescription(sdp=sdp, type="offer")
            await self.pc.setRemoteDescription(offer)

            # Use explicit role if provided, otherwise fall back to detection
            if participant_role == "producer":
                self.is_producer = True
                self.is_consumer = False
                logger.info(f"WebRTC {self.client_id} set as PRODUCER (explicit role)")
            elif participant_role == "consumer":
                self.is_consumer = True
                self.is_producer = False
                room = self.video_core.rooms.get(self.room_id)
                recovery_config = room.recovery_config if room else RecoveryConfig()
                self.video_track = VideoFrameTrack(recovery_config)
                self.pc.addTrack(self.video_track)
                logger.info(
                    f"WebRTC {self.client_id} set as CONSUMER (explicit role) - video track added"
                )
            else:
                # Auto-detection logic (fallback)
                has_recvonly = "a=recvonly" in sdp
                has_sendonly = "a=sendonly" in sdp
                has_video = "m=video" in sdp

                # Check if there are video track sources in the offer (indicates producer)
                has_video_sources = "a=ssrc:" in sdp and "m=video" in sdp

                logger.info(f"🔍 Role detection for {self.client_id}:")
                logger.info(f"   - has_recvonly: {has_recvonly}")
                logger.info(f"   - has_sendonly: {has_sendonly}")
                logger.info(f"   - has_video: {has_video}")
                logger.info(f"   - has_video_sources: {has_video_sources}")

                if has_recvonly:
                    is_consumer_request = True
                    logger.info("   - CONSUMER detected: has a=recvonly")
                elif has_sendonly or has_video_sources:
                    is_consumer_request = False
                    logger.info(
                        "   - PRODUCER detected: has a=sendonly or video sources"
                    )
                elif has_video:
                    # Default: if it has video but no clear direction, assume consumer
                    is_consumer_request = True
                    logger.info(
                        "   - CONSUMER detected: has video but no clear direction"
                    )
                else:
                    # No video at all, treat as consumer
                    is_consumer_request = True
                    logger.info("   - CONSUMER detected: no video")

                if is_consumer_request:
                    # This is a consumer - add video track for sending TO the consumer
                    self.is_consumer = True
                    room = self.video_core.rooms.get(self.room_id)
                    recovery_config = room.recovery_config if room else RecoveryConfig()
                    self.video_track = VideoFrameTrack(recovery_config)
                    self.pc.addTrack(self.video_track)
                    logger.info(
                        f"WebRTC {self.client_id} is now a CONSUMER - video track added"
                    )
                else:
                    # This is a producer
                    self.is_consumer = False
                    self.is_producer = True
                    logger.info(f"WebRTC {self.client_id} is a PRODUCER")

            # Create answer
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)

            # Wait for ICE gathering with timeout
            timeout_count = 0
            while self.pc.iceGatheringState != "complete" and timeout_count < 50:
                await asyncio.sleep(0.1)
                timeout_count += 1

            if timeout_count >= 50:
                logger.warning(f"ICE gathering timeout for {self.client_id}")

        except Exception:
            logger.exception(f"Error in handle_offer for {self.client_id}")
            raise
        else:
            return self.pc.localDescription.sdp

    async def add_ice_candidate(self, candidate_data: dict):
        """Add ICE candidate (from old code)"""
        try:
            if candidate_data.get("end"):
                return

            candidate_str = candidate_data.get("candidate", "")
            sdp_mid = candidate_data.get("sdpMid")
            sdp_m_line_index = candidate_data.get("sdpMLineIndex")

            if not candidate_str:
                logger.debug(f"Skipping empty ICE candidate for {self.client_id}")
                return

            # Parse the candidate string
            parts = candidate_str.split()
            if len(parts) < 8 or not parts[0].startswith("candidate:"):
                logger.warning(
                    f"Invalid candidate format for {self.client_id}: {candidate_str}"
                )
                return

            try:
                foundation = parts[0].split(":")[1]
                component = int(parts[1])
                protocol = parts[2].lower()
                priority = int(parts[3])
                ip = parts[4]
                port = int(parts[5])
                typ = parts[7] if parts[6] == "typ" else "host"

                candidate = RTCIceCandidate(
                    foundation=foundation,
                    component=component,
                    protocol=protocol,
                    priority=priority,
                    ip=ip,
                    port=port,
                    type=typ,
                    sdpMid=sdp_mid,
                    sdpMLineIndex=sdp_m_line_index,
                )

                await self.pc.addIceCandidate(candidate)
                logger.debug(f"ICE candidate added for {self.client_id}: {typ}")

            except (ValueError, IndexError):
                logger.exception(f"Failed to parse ICE candidate for {self.client_id}")

        except Exception:
            logger.exception(f"Failed to add ICE candidate for {self.client_id}")

    def send_video_frame(self, frame_data: bytes):
        """Send video frame to consumer"""
        if self.is_consumer and self.video_track:
            self.video_track.add_frame(frame_data)

    async def close(self):
        """Close connection"""
        if self.pc:
            await self.pc.close()

    def _add_background_task(self, coro: Coroutine):
        """Add a background task with automatic cleanup"""
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task


# ============= VIDEO ROOM (simplified) =============


class VideoRoom:
    """Simple video room with producer/consumer pattern"""

    def __init__(
        self,
        room_id: str,
        workspace_id: str,
        config: VideoConfig = None,
        recovery_config: RecoveryConfig = None,
    ):
        self.id = room_id
        self.workspace_id = workspace_id
        self.config = config or VideoConfig()
        self.recovery_config = recovery_config or RecoveryConfig()

        # Participants (same pattern as robotics)
        self.producer: str | None = None
        self.consumers: list[str] = []

        # Video state
        self.last_frame: bytes | None = None
        self.frame_count = 0
        self.total_bytes = 0
        self.start_time = datetime.now(tz=UTC)
        self.last_frame_time: datetime | None = None


# ============= VIDEO CORE (main class) =============


class VideoCore:
    """Core video system - simplified from old complex system with workspace support"""

    def __init__(self):
        # Nested structure: workspace_id -> room_id -> VideoRoom
        self.workspaces: dict[str, dict[str, VideoRoom]] = {}
        self.websocket_connections: dict[str, WebSocket] = {}
        self.webrtc_connections: dict[str, WebRTCConnection] = {}
        self.connection_metadata: dict[str, dict] = {}
        # Track background tasks to prevent garbage collection
        self.background_tasks: set = set()

    # ============= ROOM MANAGEMENT (same pattern as robotics) =============

    def create_room(
        self,
        workspace_id: str | None = None,
        room_id: str | None = None,
        config: VideoConfig = None,
        recovery_config: RecoveryConfig = None,
    ) -> tuple[str, str]:
        """Create video room and return (workspace_id, room_id)"""
        workspace_id = workspace_id or str(uuid.uuid4())
        room_id = room_id or str(uuid.uuid4())

        # Initialize workspace if it doesn't exist
        if workspace_id not in self.workspaces:
            self.workspaces[workspace_id] = {}

        room = VideoRoom(room_id, workspace_id, config, recovery_config)
        self.workspaces[workspace_id][room_id] = room
        logger.info(f"Created video room {room_id} in workspace {workspace_id}")
        return workspace_id, room_id

    def list_rooms(self, workspace_id: str) -> list[dict]:
        """List all video rooms in a specific workspace"""
        if workspace_id not in self.workspaces:
            return []

        return [
            {
                "id": room.id,
                "workspace_id": room.workspace_id,
                "participants": {
                    "producer": room.producer,
                    "consumers": room.consumers,
                    "total": len(room.consumers) + (1 if room.producer else 0),
                },
                "frame_count": room.frame_count,
                "config": {
                    "resolution": room.config.resolution,
                    "framerate": room.config.framerate,
                    # "encoding": room.config.encoding.value
                    # if room.config.encoding
                    # else "vp8",
                    "bitrate": room.config.bitrate,
                    "quality": room.config.quality,
                },
                "has_producer": room.producer is not None,
                "active_consumers": len(room.consumers),
            }
            for room in self.workspaces[workspace_id].values()
        ]

    def delete_room(self, workspace_id: str, room_id: str) -> bool:
        """Delete video room from workspace"""
        if (
            workspace_id not in self.workspaces
            or room_id not in self.workspaces[workspace_id]
        ):
            return False

        # Cleanup connections
        for conn_id in list(self.webrtc_connections.keys()):
            conn = self.webrtc_connections[conn_id]
            if (
                conn.room_id == room_id
                and getattr(conn, "workspace_id", None) == workspace_id
            ):
                self._add_background_task(conn.close())
                del self.webrtc_connections[conn_id]

        del self.workspaces[workspace_id][room_id]
        logger.info(f"Deleted video room {room_id} from workspace {workspace_id}")
        return True

    def get_room_state(self, workspace_id: str, room_id: str) -> dict:
        """Get room state"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return {"error": "Room not found"}

        return {
            "room_id": room_id,
            "workspace_id": workspace_id,
            "participants": {
                "producer": room.producer,
                "consumers": room.consumers,
                "total": len(room.consumers) + (1 if room.producer else 0),
            },
            "frame_count": room.frame_count,
            "last_frame_time": room.last_frame_time,
            "current_config": {
                "resolution": room.config.resolution,
                "framerate": room.config.framerate,
                "encoding": room.config.encoding.value
                if room.config.encoding
                else "vp8",
                "bitrate": room.config.bitrate,
                "quality": room.config.quality,
            },
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

    def get_room_info(self, workspace_id: str, room_id: str) -> dict:
        """Get basic room info"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return {"error": "Room not found"}

        return {
            "id": room.id,
            "workspace_id": room.workspace_id,
            "participants": {
                "producer": room.producer,
                "consumers": room.consumers,
                "total": len(room.consumers) + (1 if room.producer else 0),
            },
            "frame_count": room.frame_count,
            "config": {
                "resolution": room.config.resolution,
                "framerate": room.config.framerate,
                "encoding": room.config.encoding.value
                if room.config.encoding
                else "vp8",
                "bitrate": room.config.bitrate,
                "quality": room.config.quality,
            },
            "has_producer": room.producer is not None,
            "active_consumers": len(room.consumers),
        }

    def _get_room(self, workspace_id: str, room_id: str) -> VideoRoom | None:
        """Get room by workspace and room ID"""
        if workspace_id not in self.workspaces:
            return None
        return self.workspaces[workspace_id].get(room_id)

    # ============= PARTICIPANT MANAGEMENT =============

    def join_room(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
    ) -> bool:
        """Join room as producer or consumer"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return False

        if role == ParticipantRole.PRODUCER:
            if room.producer is None:
                room.producer = participant_id
                logger.info(
                    f"Producer {participant_id} joined video room {room_id} in workspace {workspace_id}"
                )

                # Broadcast producer join to existing consumers
                self._add_background_task(
                    self._broadcast_participant_joined(
                        workspace_id, room_id, participant_id, role
                    )
                )
                return True
            logger.warning(
                f"Producer {participant_id} failed to join room {room_id} - room already has producer"
            )
            return False

        if role == ParticipantRole.CONSUMER:
            if participant_id not in room.consumers:
                room.consumers.append(participant_id)
                logger.info(
                    f"Consumer {participant_id} joined video room {room_id} in workspace {workspace_id}"
                )

                # Broadcast consumer join to producer and other consumers
                self._add_background_task(
                    self._broadcast_participant_joined(
                        workspace_id, room_id, participant_id, role
                    )
                )
                return True
            return False

        return False

    def leave_room(self, workspace_id: str, room_id: str, participant_id: str):
        """Leave room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        role = None
        if room.producer == participant_id:
            room.producer = None
            role = ParticipantRole.PRODUCER
            logger.info(
                f"Producer {participant_id} left video room {room_id} in workspace {workspace_id}"
            )
        elif participant_id in room.consumers:
            room.consumers.remove(participant_id)
            role = ParticipantRole.CONSUMER
            logger.info(
                f"Consumer {participant_id} left video room {room_id} in workspace {workspace_id}"
            )

        # Broadcast participant left event
        if role:
            self._add_background_task(
                self._broadcast_participant_left(
                    workspace_id, room_id, participant_id, role
                )
            )

    # ============= WEBRTC HANDLING =============

    async def handle_webrtc_signal(
        self,
        workspace_id: str,
        room_id: str,
        client_id: str,
        message: RawWebRTCSignalingMessage,
        participant_role: str | None = None,
    ):
        """Handle WebRTC signaling for peer-to-peer connections"""
        if (
            workspace_id not in self.workspaces
            or room_id not in self.workspaces[workspace_id]
        ):
            msg = f"Room {room_id} not found in workspace {workspace_id}"
            raise ValueError(msg)

        if message["type"] == RawWebRTCMessageType.OFFER:
            # Check if this is a targeted offer from producer to consumer
            target_consumer = message.get("target_consumer")

            if target_consumer and participant_role == "producer":
                # Producer sending offer to specific consumer - forward it
                logger.info(
                    f"🔄 Forwarding offer from producer {client_id} to consumer {target_consumer}"
                )

                output_message: WebRTCOfferMessageDict = {
                    "type": MessageType.WEBRTC_OFFER,
                    "offer": {"type": "offer", "sdp": message["sdp"]},
                    "from_producer": client_id,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }

                await self._send_to_participant(target_consumer, output_message)
                return {"success": True, "message": "Offer forwarded to consumer"}

            # For peer-to-peer, we don't handle server-side WebRTC connections
            logger.info(
                f"Ignoring server WebRTC offer from {client_id} - using peer-to-peer"
            )
            return {
                "success": True,
                "message": "Peer-to-peer mode - no server WebRTC processing",
            }

        if message["type"] == RawWebRTCMessageType.ANSWER:
            # Handle answer from consumer back to producer
            from_consumer = client_id
            target_producer = message.get("target_producer")

            if target_producer:
                logger.info(
                    f"🔄 Forwarding answer from consumer {from_consumer} to producer {target_producer}"
                )

                output_message: WebRTCAnswerMessageDict = {
                    "type": MessageType.WEBRTC_ANSWER,
                    "answer": {"type": "answer", "sdp": message["sdp"]},
                    "from_consumer": from_consumer,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }

                await self._send_to_participant(target_producer, output_message)
                return {"success": True, "message": "Answer forwarded to producer"}

        elif message["type"] == RawWebRTCMessageType.ICE:
            # Forward ICE candidates between peers
            target_consumer = message.get("target_consumer")
            target_producer = message.get("target_producer")

            if target_consumer and participant_role == "producer":
                output_message: WebRTCIceMessageDict = {
                    "type": MessageType.WEBRTC_ICE,
                    "candidate": message["candidate"],
                    "from_producer": client_id,
                    "from_consumer": None,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }

                await self._send_to_participant(target_consumer, output_message)
                return {
                    "success": True,
                    "message": "ICE candidate forwarded to consumer",
                }
            if target_producer and participant_role == "consumer":
                output_message: WebRTCIceMessageDict = {
                    "type": MessageType.WEBRTC_ICE,
                    "candidate": message["candidate"],
                    "from_producer": None,
                    "from_consumer": client_id,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }

                await self._send_to_participant(target_producer, output_message)
                return {
                    "success": True,
                    "message": "ICE candidate forwarded to producer",
                }

        return None

    async def broadcast_to_consumers(
        self, workspace_id: str, room_id: str, frame_data: bytes
    ):
        """Broadcast frame to all consumers"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return 0

        consumer_count = 0
        for consumer_id in room.consumers:
            consumer_conn = self.webrtc_connections.get(consumer_id)
            if consumer_conn and consumer_conn.is_consumer:
                try:
                    consumer_conn.send_video_frame(frame_data)
                    consumer_count += 1
                except Exception:
                    logger.exception(f"Error sending frame to {consumer_id}")

        if consumer_count > 0:
            logger.debug(f"Broadcasted frame to {consumer_count} consumers")

        return consumer_count

    # ============= WEBSOCKET HANDLING =============

    async def handle_websocket(
        self, websocket: WebSocket, workspace_id: str, room_id: str
    ):
        """Handle WebSocket connection for room management"""
        await websocket.accept()

        participant_id: str | None = None
        role: ParticipantRole | None = None

        try:
            # Get join message
            data = await websocket.receive_text()
            join_msg = json.loads(data)

            participant_id = join_msg["participant_id"]
            role = ParticipantRole(join_msg["role"])

            # Join room
            if not self.join_room(workspace_id, room_id, participant_id, role):
                error_message: ErrorMessageDict = {
                    "type": MessageType.ERROR,
                    "message": "Cannot join room",
                    "code": None,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }
                await websocket.send_text(json.dumps(error_message))
                await websocket.close()
                return

            self.websocket_connections[participant_id] = websocket
            self.connection_metadata[participant_id] = {
                "workspace_id": workspace_id,
                "room_id": room_id,
                "participant_id": participant_id,
                "role": role,
                "connected_at": datetime.now(tz=UTC),
                "last_activity": datetime.now(tz=UTC),
                "message_count": 0,
            }

            # Send join confirmation
            joined_message: JoinedMessageDict = {
                "type": MessageType.JOINED,
                "room_id": room_id,
                "role": role,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await websocket.send_text(json.dumps(joined_message))

            # Handle messages
            async for message in websocket.iter_text():
                try:
                    msg = json.loads(message)
                    await self._handle_websocket_message(
                        workspace_id, room_id, participant_id, role, msg
                    )
                except json.JSONDecodeError:
                    logger.exception(f"Invalid JSON from {participant_id}")
                except Exception:
                    logger.exception("WebSocket message error")

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {participant_id}")
        except Exception:
            logger.exception("WebSocket error")
        finally:
            # Cleanup
            if participant_id:
                metadata = self.connection_metadata.get(participant_id)
                if metadata:
                    self.leave_room(
                        metadata["workspace_id"], metadata["room_id"], participant_id
                    )
                if participant_id in self.websocket_connections:
                    del self.websocket_connections[participant_id]
                if participant_id in self.connection_metadata:
                    del self.connection_metadata[participant_id]

    async def _handle_websocket_message(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
        message: WebSocketMessageDict,
    ):
        """Handle incoming WebSocket message"""
        # Update activity tracking
        if participant_id in self.connection_metadata:
            self.connection_metadata[participant_id]["last_activity"] = datetime.now(
                tz=UTC
            )
            self.connection_metadata[participant_id]["message_count"] += 1

        # Handle heartbeat
        if message["type"] == MessageType.HEARTBEAT:
            heartbeat_ack: HeartbeatAckMessageDict = {
                "type": MessageType.HEARTBEAT_ACK,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._send_to_participant(participant_id, heartbeat_ack)
            return

        # Handle stream started notification
        if message["type"] == MessageType.STREAM_STARTED:
            logger.info(
                f"Stream started by {participant_id} in room {room_id} (workspace {workspace_id})"
            )
            config = message.get("config", {})

            # Broadcast to other participants
            broadcast_message: StreamStartedMessageDict = {
                "type": MessageType.STREAM_STARTED,
                "config": config,
                "participant_id": participant_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Handle stream stopped notification
        if message["type"] == MessageType.STREAM_STOPPED:
            logger.info(
                f"Stream stopped by {participant_id} in room {room_id} (workspace {workspace_id})"
            )
            reason = message.get("reason")

            # Broadcast to other participants
            broadcast_message: StreamStoppedMessageDict = {
                "type": MessageType.STREAM_STOPPED,
                "participant_id": participant_id,
                "reason": reason,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Handle video config update
        if message["type"] == MessageType.VIDEO_CONFIG_UPDATE:
            logger.info(
                f"Video config updated by {participant_id} in room {room_id} (workspace {workspace_id})"
            )
            config = message.get("config", {})

            # Update room config if producer
            if role == ParticipantRole.PRODUCER:
                room = self._get_room(workspace_id, room_id)
                if room:
                    # Update room's video config
                    if "resolution" in config:
                        room.config.resolution = config["resolution"]
                    if "framerate" in config:
                        room.config.framerate = config["framerate"]
                    if "quality" in config:
                        room.config.quality = config["quality"]
                    if "encoding" in config:
                        room.config.encoding = config["encoding"]
                    if "bitrate" in config:
                        room.config.bitrate = config["bitrate"]

            # Broadcast to other participants
            broadcast_message: VideoConfigUpdateMessageDict = {
                "type": MessageType.VIDEO_CONFIG_UPDATE,
                "config": config,
                "source": participant_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Handle status update
        if message["type"] == MessageType.STATUS_UPDATE:
            logger.info(
                f"Status update from {participant_id} in room {room_id} (workspace {workspace_id})"
            )
            status = message.get("status", "unknown")
            data = message.get("data")

            # Broadcast to other participants
            broadcast_message: StatusUpdateMessageDict = {
                "type": MessageType.STATUS_UPDATE,
                "status": status,
                "data": data,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Handle stream stats
        if message["type"] == MessageType.STREAM_STATS:
            logger.debug(
                f"Stream stats from {participant_id} in room {room_id} (workspace {workspace_id})"
            )
            stats = message.get("stats", {})

            # Broadcast to other participants (typically from producer to consumers)
            broadcast_message: StreamStatsMessageDict = {
                "type": MessageType.STREAM_STATS,
                "stats": stats,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Handle emergency stop
        if message["type"] == MessageType.EMERGENCY_STOP:
            reason = message.get("reason", "Emergency stop triggered")
            logger.warning(
                f"Emergency stop by {participant_id} in room {room_id} (workspace {workspace_id}): {reason}"
            )

            # Broadcast to all participants
            broadcast_message: EmergencyStopMessageDict = {
                "type": MessageType.EMERGENCY_STOP,
                "reason": reason,
                "source": participant_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(workspace_id, room_id, broadcast_message)
            return

        # Handle recovery triggered (from consumer typically)
        if message["type"] == MessageType.RECOVERY_TRIGGERED:
            policy = message.get("policy")
            reason = message.get("reason", "Recovery triggered")
            logger.info(
                f"Recovery triggered by {participant_id} in room {room_id} (workspace {workspace_id}): {policy} - {reason}"
            )

            # Broadcast to other participants
            broadcast_message: RecoveryTriggeredMessageDict = {
                "type": MessageType.RECOVERY_TRIGGERED,
                "policy": policy,
                "reason": reason,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            await self._broadcast_to_room(
                workspace_id, room_id, broadcast_message, exclude=participant_id
            )
            return

        # Log unhandled message types
        logger.info(f"Unhandled message type {message['type']} from {participant_id}")

    async def _broadcast_to_room(
        self,
        workspace_id: str,
        room_id: str,
        message: WebSocketMessageDict,
        exclude: str | None = None,
    ):
        """Broadcast message to all participants in a room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        participants = []
        if room.producer:
            participants.append(room.producer)
        participants.extend(room.consumers)

        for participant_id in participants:
            if exclude and participant_id == exclude:
                continue
            await self._send_to_participant(participant_id, message)

    async def _send_to_participant(
        self, participant_id: str, message: WebSocketMessageDict
    ):
        """Send message to specific participant"""
        if participant_id in self.websocket_connections:
            try:
                await self.websocket_connections[participant_id].send_text(
                    json.dumps(message)
                )
            except Exception:
                logger.exception(f"Error sending message to {participant_id}")
                if participant_id in self.websocket_connections:
                    del self.websocket_connections[participant_id]

    async def _broadcast_participant_joined(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
    ):
        """Broadcast participant joined event to other participants in the room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        participants: list[str] = []
        if room.producer:
            participants.append(room.producer)
        participants.extend(room.consumers)

        participant_joined_message: ParticipantJoinedMessageDict = {
            "type": MessageType.PARTICIPANT_JOINED,
            "room_id": room_id,
            "participant_id": participant_id,
            "role": role,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        for other_participant_id in participants:
            if other_participant_id == participant_id:
                continue
            await self._send_to_participant(
                other_participant_id, participant_joined_message
            )

    async def _broadcast_participant_left(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
    ):
        """Broadcast participant left event to other participants in the room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        participants: list[str] = []
        if room.producer:
            participants.append(room.producer)
        participants.extend(room.consumers)

        participant_left_message: dict = {
            "type": MessageType.PARTICIPANT_LEFT,
            "room_id": room_id,
            "participant_id": participant_id,
            "role": role,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        for other_participant_id in participants:
            if other_participant_id == participant_id:
                continue
            await self._send_to_participant(
                other_participant_id, participant_left_message
            )

    def _add_background_task(self, coro: Coroutine):
        """Add a background task with automatic cleanup"""
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task
