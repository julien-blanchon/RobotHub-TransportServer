"""
Producer client for video streaming in LeRobot Arena
"""

import asyncio
import fractions
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import av
import cv2
import numpy as np
from aiortc import RTCIceCandidate, RTCSessionDescription, VideoStreamTrack

from .core import VideoClientCore
from .types import (
    ClientOptions,
    ParticipantRole,
    StatusUpdateCallback,
    StreamStatsCallback,
    VideoConfig,
)

logger = logging.getLogger(__name__)


class CameraVideoTrack(VideoStreamTrack):
    """Custom video track for camera capture using OpenCV"""

    def __init__(
        self,
        device_id: int = 0,
        resolution: dict[str, int] | None = None,
        frame_rate: int = 30,
    ):
        super().__init__()
        self.device_id = device_id
        self.resolution = resolution or {"width": 640, "height": 480}
        self.frame_rate = frame_rate
        self.cap: cv2.VideoCapture | None = None
        self._frame_time = 1.0 / frame_rate

    async def recv(self) -> Any:
        """Receive the next video frame"""
        if self.cap is None:
            raise ValueError("Camera not initialized")

        # Calculate timing for consistent frame rate
        start_time = time.time()

        # Capture frame
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError("Failed to capture frame from camera")

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        av_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        av_frame.pts = self._get_next_pts()
        av_frame.time_base = fractions.Fraction(1, 90000)

        # Maintain frame rate
        elapsed = time.time() - start_time
        sleep_time = max(0, self._frame_time - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

        return av_frame

    def _get_next_pts(self) -> int:
        """Get the next presentation timestamp"""
        if not hasattr(self, "_pts"):
            self._pts = 0
        else:
            self._pts += int(
                90000 / self.frame_rate
            )  # 90000 is our time_base denominator
        return self._pts

    async def start_capture(self) -> None:
        """Start camera capture"""
        if self.cap is not None:
            return

        self.cap = cv2.VideoCapture(self.device_id)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open camera device {self.device_id}")

        # Configure camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution["width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution["height"])
        self.cap.set(cv2.CAP_PROP_FPS, self.frame_rate)

        # Verify actual settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        logger.info(
            f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps"
        )

    async def stop_capture(self) -> None:
        """Stop camera capture"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class CustomVideoTrack(VideoStreamTrack):
    """Custom video track that accepts frames from a user-provided source"""

    def __init__(
        self,
        frame_source: Callable[[], Awaitable[np.ndarray | None]],
        frame_rate: int = 30,
    ):
        super().__init__()
        self.frame_source = frame_source
        self.frame_rate = frame_rate
        self._frame_time = 1.0 / frame_rate

    async def recv(self) -> Any:
        """Receive the next video frame from the custom source"""
        start_time = time.time()

        try:
            # Get frame from source
            frame_np = await self.frame_source()

            if frame_np is not None:
                # Validate frame format
                if len(frame_np.shape) != 3 or frame_np.shape[2] != 3:
                    logger.warning(
                        f"Invalid frame shape: {frame_np.shape}, expected (H, W, 3)"
                    )
                    frame_np = np.zeros((480, 640, 3), dtype=np.uint8)

                # Create video frame directly from RGB data
                frame = av.VideoFrame.from_ndarray(frame_np, format="rgb24")
                frame.pts = self._get_next_pts()
                frame.time_base = fractions.Fraction(1, self.frame_rate)

            else:
                # No frame available - create a black frame
                logger.debug("No frame from source, creating black frame")
                black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(black_frame, format="rgb24")
                frame.pts = self._get_next_pts()
                frame.time_base = fractions.Fraction(1, self.frame_rate)

            # Maintain consistent frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, self._frame_time - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            return frame

        except Exception as e:
            logger.error(f"Error in custom video track recv: {e}")
            # Return black frame on any error
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(black_frame, format="rgb24")
            frame.pts = self._get_next_pts()
            frame.time_base = fractions.Fraction(1, self.frame_rate)
            return frame

    def _get_next_pts(self) -> int:
        """Get the next presentation timestamp"""
        if not hasattr(self, "_pts"):
            self._pts = 0
        else:
            self._pts += int(90000 / self.frame_rate)
        return self._pts


class VideoProducer(VideoClientCore):
    """Producer client for video streaming in LeRobot Arena"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        options: ClientOptions | None = None,
    ):
        super().__init__(base_url, options)

        # Multiple peer connections - one per consumer
        self.consumer_connections: dict[str, Any] = {}

        # Video tracks
        self.camera_track: CameraVideoTrack | None = None
        self.custom_track: CustomVideoTrack | None = None

        # Event callbacks
        self.on_status_update_callback: StatusUpdateCallback | None = None
        self.on_stream_stats_callback: StreamStatsCallback | None = None

    # ============= PRODUCER CONNECTION =============

    async def connect(
        self, workspace_id: str, room_id: str, participant_id: str | None = None
    ) -> bool:
        """Connect to a room as producer"""
        success = await self.connect_to_room(
            workspace_id, room_id, ParticipantRole.PRODUCER, participant_id
        )

        if success:
            logger.info("🎬 Connected as video producer")
            # Check for existing consumers and initiate connections after a delay
            asyncio.create_task(self._connect_to_existing_consumers())

        return success

    async def _connect_to_existing_consumers(self) -> None:
        """Connect to existing consumers in the room"""
        await asyncio.sleep(1)  # Give time for connection to stabilize

        if not self.workspace_id or not self.room_id:
            return

        try:
            room_info = await self.get_room_info(self.workspace_id, self.room_id)
            for consumer_id in room_info.participants.consumers:
                if consumer_id not in self.consumer_connections:
                    logger.info(f"🔄 Connecting to existing consumer {consumer_id}")
                    await self.initiate_webrtc_with_consumer(consumer_id)
        except Exception as e:
            logger.error(f"Failed to connect to existing consumers: {e}")

    async def _restart_connections_with_new_stream(self) -> None:
        """Restart all connections with new stream tracks"""
        logger.info("🔄 Restarting connections with new stream...")

        # Close all existing connections
        for consumer_id, peer_connection in list(self.consumer_connections.items()):
            await peer_connection.close()
            logger.info(f"🧹 Closed existing connection to consumer {consumer_id}")
        self.consumer_connections.clear()

        # Get current consumers and restart connections
        try:
            if self.workspace_id and self.room_id:
                room_info = await self.get_room_info(self.workspace_id, self.room_id)
                for consumer_id in room_info.participants.consumers:
                    logger.info(
                        f"🔄 Creating new connection to consumer {consumer_id}..."
                    )
                    await self.initiate_webrtc_with_consumer(consumer_id)
        except Exception as e:
            logger.error(f"Failed to restart connections: {e}")

    def _create_peer_connection_for_consumer(self, consumer_id: str) -> Any:
        """Create a peer connection for a specific consumer"""
        from aiortc import RTCPeerConnection

        peer_connection = RTCPeerConnection()

        # Add current track if available
        current_track = self.get_video_track()
        if current_track:
            peer_connection.addTrack(current_track)

        # Store the connection
        self.consumer_connections[consumer_id] = peer_connection

        # Set up event handlers
        @peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            state = peer_connection.connectionState
            logger.info(f"🔌 WebRTC connection state for {consumer_id}: {state}")

            if state in ["failed", "disconnected"]:
                logger.warning(
                    f"⚠️ Connection to {consumer_id} failed, attempting restart..."
                )
                await asyncio.sleep(2)
                await self._restart_connection_to_consumer(consumer_id)

        @peer_connection.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate and self.workspace_id and self.room_id and self.participant_id:
                await self.send_webrtc_signal(
                    self.workspace_id,
                    self.room_id,
                    self.participant_id,
                    {
                        "type": "ice",
                        "candidate": {
                            "candidate": candidate.candidate,
                            "sdpMid": candidate.sdpMid,
                            "sdpMLineIndex": candidate.sdpMLineIndex,
                        },
                        "target_consumer": consumer_id,
                    },
                )

        return peer_connection

    async def _restart_connection_to_consumer(self, consumer_id: str) -> None:
        """Restart connection to a consumer"""
        logger.info(f"🔄 Restarting connection to consumer {consumer_id}")
        await self.initiate_webrtc_with_consumer(consumer_id)

    def _handle_consumer_left(self, consumer_id: str) -> None:
        """Handle consumer leaving - cleanup connection"""
        if consumer_id in self.consumer_connections:
            peer_connection = self.consumer_connections[consumer_id]
            asyncio.create_task(peer_connection.close())
            del self.consumer_connections[consumer_id]
            logger.info(f"🧹 Cleaned up peer connection for consumer {consumer_id}")

    # ============= PRODUCER METHODS =============

    async def start_camera(
        self, device_id: int = 0, constraints: dict[str, Any] | None = None
    ) -> Any:
        """Start camera streaming"""
        if not self.connected:
            raise ValueError("Must be connected to start camera")

        # Create camera track
        resolution = None
        if constraints and "video" in constraints:
            video_constraints = constraints["video"]
            if "width" in video_constraints and "height" in video_constraints:
                resolution = {
                    "width": video_constraints["width"].get("ideal", 640),
                    "height": video_constraints["height"].get("ideal", 480),
                }

        framerate = 30
        if (
            constraints
            and "video" in constraints
            and "frameRate" in constraints["video"]
        ):
            framerate = constraints["video"]["frameRate"].get("ideal", 30)

        self.camera_track = CameraVideoTrack(device_id, resolution, framerate)
        await self.camera_track.start_capture()

        # Store as local stream and restart connections with new tracks
        self.local_stream = self.camera_track
        await self._restart_connections_with_new_stream()

        # Notify about stream start
        await self._notify_stream_started()

        return self.camera_track

    async def start_screen_share(self) -> Any:
        """Start screen sharing (placeholder - would need screen capture implementation)"""
        if not self.connected:
            raise ValueError("Must be connected to start screen share")

        # For now, create a simple pattern as a placeholder
        async def screen_frame_source() -> np.ndarray | None:
            # Create a simple animated pattern
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            t = time.time()

            # Create moving gradient
            for y in range(480):
                for x in range(640):
                    r = int(128 + 127 * np.sin(t + x * 0.01))
                    g = int(128 + 127 * np.sin(t + y * 0.01 + 2))
                    b = int(128 + 127 * np.sin(t + (x + y) * 0.005 + 4))
                    frame[y, x] = [r, g, b]

            return frame

        self.custom_track = CustomVideoTrack(screen_frame_source, 30)

        # Store as local stream and restart connections with new tracks
        self.local_stream = self.custom_track
        await self._restart_connections_with_new_stream()

        # Notify about stream start
        await self._notify_stream_started()

        logger.info("📺 Screen share started and ready for consumers")

        return self.custom_track

    async def start_custom_stream(
        self, frame_source: Callable[[], Awaitable[np.ndarray | None]]
    ) -> Any:
        """Start streaming from a custom frame source"""
        if not self.connected:
            raise ValueError("Must be connected to start custom stream")

        # Create custom track
        self.custom_track = CustomVideoTrack(frame_source, 30)

        # Store as local stream and restart connections with new tracks
        self.local_stream = self.custom_track
        await self._restart_connections_with_new_stream()

        # Notify about stream start
        await self._notify_stream_started()

        logger.info("📺 Custom stream started and ready for consumers")

        return self.custom_track

    async def stop_streaming(self) -> None:
        """Stop video streaming"""
        if not self.connected or not self.websocket:
            raise ValueError("Must be connected to stop streaming")

        # Close all consumer connections
        for consumer_id, peer_connection in list(self.consumer_connections.items()):
            await peer_connection.close()
            logger.info(f"🧹 Closed connection to consumer {consumer_id}")
        self.consumer_connections.clear()

        # Stop camera track
        if self.camera_track:
            await self.camera_track.stop_capture()
            self.camera_track = None

        # Stop custom track
        if self.custom_track:
            self.custom_track = None

        # Stop local stream
        self.stop_producing()

        # Notify about stream stop
        await self._notify_stream_stopped()

    async def update_video_config(self, config: VideoConfig) -> None:
        """Update video configuration"""
        if not self.connected or not self.websocket:
            raise ValueError("Must be connected to update video config")

        message = {
            "type": "video_config_update",
            "config": self._video_config_to_dict(config),
            "timestamp": time.time(),
        }

        await self.websocket.send(json.dumps(message))

    async def send_emergency_stop(self, reason: str = "Emergency stop") -> None:
        """Send emergency stop signal"""
        if not self.connected or not self.websocket:
            raise ValueError("Must be connected to send emergency stop")

        message = {"type": "emergency_stop", "reason": reason, "timestamp": time.time()}

        await self.websocket.send(json.dumps(message))

    # ============= WEBRTC NEGOTIATION =============

    async def initiate_webrtc_with_consumer(self, consumer_id: str) -> None:
        """Initiate WebRTC connection with a consumer"""
        if not self.workspace_id or not self.room_id or not self.participant_id:
            logger.warning("WebRTC not ready, skipping negotiation with consumer")
            return

        # Clean up existing connection if any
        if consumer_id in self.consumer_connections:
            existing_conn = self.consumer_connections[consumer_id]
            await existing_conn.close()
            del self.consumer_connections[consumer_id]

        try:
            logger.info(f"🔄 Creating WebRTC offer for consumer {consumer_id}...")

            # Create a new peer connection specifically for this consumer
            peer_connection = self._create_peer_connection_for_consumer(consumer_id)

            # Create offer with this consumer's peer connection
            offer = await peer_connection.createOffer()
            await peer_connection.setLocalDescription(offer)

            logger.info(f"📤 Sending WebRTC offer to consumer {consumer_id}...")

            # Send offer to server/consumer
            await self.send_webrtc_signal(
                self.workspace_id,
                self.room_id,
                self.participant_id,
                {
                    "type": offer.type,
                    "sdp": offer.sdp,
                    "target_consumer": consumer_id,
                },
            )

            logger.info(f"✅ WebRTC offer sent to consumer {consumer_id}")
        except Exception as e:
            logger.error(f"Failed to initiate WebRTC with consumer {consumer_id}: {e}")

    async def handle_webrtc_answer(
        self, answer_data: dict[str, Any], from_consumer: str
    ) -> None:
        """Handle WebRTC answer from consumer"""
        try:
            logger.info(f"📥 Received WebRTC answer from consumer {from_consumer}")

            peer_connection = self.consumer_connections.get(from_consumer)
            if not peer_connection:
                logger.warning(f"No peer connection found for consumer {from_consumer}")
                return

            # Set remote description on the correct peer connection
            answer = RTCSessionDescription(
                sdp=answer_data["sdp"], type=answer_data["type"]
            )
            await peer_connection.setRemoteDescription(answer)

            logger.info(
                f"✅ WebRTC negotiation completed with consumer {from_consumer}"
            )
        except Exception as e:
            logger.error(f"Failed to handle WebRTC answer from {from_consumer}: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"Failed to handle WebRTC answer: {e}")

    async def handle_webrtc_ice(
        self, ice_data: dict[str, Any], from_consumer: str
    ) -> None:
        """Handle WebRTC ICE candidate from consumer"""
        try:
            if not from_consumer:
                logger.warning("No consumer ID in ICE message")
                return

            peer_connection = self.consumer_connections.get(from_consumer)
            if not peer_connection:
                logger.warning(f"No peer connection found for consumer {from_consumer}")
                return

            logger.info(f"📥 Received WebRTC ICE from consumer {from_consumer}")

            # Parse ICE candidate string and create RTCIceCandidate
            candidate_str = ice_data["candidate"]
            parts = candidate_str.split()

            if len(parts) >= 8:
                candidate = RTCIceCandidate(
                    component=int(parts[1]),
                    foundation=parts[0].split(":")[1],  # Remove "candidate:" prefix
                    ip=parts[4],
                    port=int(parts[5]),
                    priority=int(parts[3]),
                    protocol=parts[2],
                    type=parts[7],  # typ value
                    sdpMid=ice_data.get("sdpMid"),
                    sdpMLineIndex=ice_data.get("sdpMLineIndex"),
                )
            else:
                logger.warning(f"Invalid ICE candidate format: {candidate_str}")
                return

            await peer_connection.addIceCandidate(candidate)

            logger.info(f"✅ WebRTC ICE handled with consumer {from_consumer}")
        except Exception as e:
            logger.error(f"Failed to handle WebRTC ICE from {from_consumer}: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"Failed to handle WebRTC ICE: {e}")

    # ============= EVENT CALLBACKS =============

    def on_status_update(self, callback: StatusUpdateCallback) -> None:
        """Set callback for status updates"""
        self.on_status_update_callback = callback

    def on_stream_stats(self, callback: StreamStatsCallback) -> None:
        """Set callback for stream statistics"""
        self.on_stream_stats_callback = callback

    # ============= MESSAGE HANDLING =============

    async def _handle_role_specific_message(self, data: dict[str, Any]) -> None:
        """Handle producer-specific messages"""
        msg_type = data.get("type")

        if msg_type == "participant_joined":
            # Check if this is a consumer joining
            if (
                data.get("role") == "consumer"
                and data.get("participant_id") != self.participant_id
            ):
                consumer_id = data.get("participant_id")
                logger.info(f"🎯 Consumer {consumer_id} joined, initiating WebRTC...")
                await self.initiate_webrtc_with_consumer(consumer_id)
        elif msg_type == "participant_left":
            # Check if this is a consumer leaving
            if data.get("role") == "consumer":
                consumer_id = data.get("participant_id")
                logger.info(f"👋 Consumer {consumer_id} left room")
                self._handle_consumer_left(consumer_id)
        elif msg_type == "webrtc_answer":
            await self.handle_webrtc_answer(
                data.get("answer", {}), data.get("from_consumer", "")
            )
        elif msg_type == "webrtc_ice":
            await self.handle_webrtc_ice(
                data.get("candidate", {}), data.get("from_consumer", "")
            )
        elif msg_type == "status_update":
            await self._handle_status_update(data)
        elif msg_type == "stream_stats":
            await self._handle_stream_stats(data)
        elif msg_type == "emergency_stop":
            logger.warning(f"Emergency stop: {data.get('reason', 'Unknown reason')}")
            if self.on_error_callback:
                self.on_error_callback(
                    f"Emergency stop: {data.get('reason', 'Unknown reason')}"
                )
        else:
            logger.warning(f"Unknown message type for producer: {msg_type}")

    async def _handle_status_update(self, data: dict[str, Any]) -> None:
        """Handle status update message"""
        if self.on_status_update_callback:
            status = data.get("status", "")
            status_data = data.get("data")
            self.on_status_update_callback(status, status_data)

    async def _handle_stream_stats(self, data: dict[str, Any]) -> None:
        """Handle stream stats message"""
        if self.on_stream_stats_callback:
            from .types import StreamStats

            stats_data = data.get("stats", {})
            stats = StreamStats(
                stream_id=stats_data.get("stream_id", ""),
                duration_seconds=stats_data.get("duration_seconds", 0.0),
                frame_count=stats_data.get("frame_count", 0),
                total_bytes=stats_data.get("total_bytes", 0),
                average_fps=stats_data.get("average_fps", 0.0),
                average_bitrate=stats_data.get("average_bitrate", 0.0),
            )
            self.on_stream_stats_callback(stats)

    # ============= UTILITY METHODS =============

    async def _notify_stream_started(self) -> None:
        """Notify server about stream start"""
        if not self.websocket:
            return

        config = {
            "resolution": self.webrtc_config.resolution,
            "framerate": self.webrtc_config.framerate,
            "bitrate": self.webrtc_config.bitrate,
        }

        message = {
            "type": "stream_started",
            "config": config,
            "participant_id": self.participant_id,
            "timestamp": time.time(),
        }

        await self.websocket.send(json.dumps(message))

    async def _notify_stream_stopped(self) -> None:
        """Notify server about stream stop"""
        if not self.websocket:
            return

        message = {
            "type": "stream_stopped",
            "participant_id": self.participant_id,
            "timestamp": time.time(),
        }

        await self.websocket.send(json.dumps(message))

    def get_video_track(self) -> VideoStreamTrack | None:
        """Get the current video track"""
        return self.camera_track or self.custom_track

    @staticmethod
    async def create_and_connect(
        base_url: str = "http://localhost:8000",
        workspace_id: str | None = None,
        room_id: str | None = None,
        participant_id: str | None = None,
    ) -> "VideoProducer":
        """Create a room and automatically connect as producer"""
        producer = VideoProducer(base_url)

        workspace_id, room_id = await producer.create_room(workspace_id, room_id)
        connected = await producer.connect(workspace_id, room_id, participant_id)

        if not connected:
            raise ValueError("Failed to connect as video producer")

        return producer

    @property
    def current_room_id(self) -> str | None:
        """Get the current room ID"""
        return self.room_id

    async def get_camera_devices(self) -> list[dict[str, Any]]:
        """Get available camera devices"""
        devices = []

        # Test up to 10 camera devices
        for device_id in range(10):
            cap = cv2.VideoCapture(device_id)
            if cap.isOpened():
                # Get device info
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                devices.append({
                    "device_id": device_id,
                    "name": f"Camera {device_id}",
                    "resolution": {"width": width, "height": height},
                    "fps": fps,
                })
                cap.release()

        return devices
