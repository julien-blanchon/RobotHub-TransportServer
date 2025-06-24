"""
Core video client for LeRobot Arena
Base class providing REST API, WebSocket, and WebRTC functionality
"""

import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp
import websockets
from aiortc import (
    RTCConfiguration,
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)

from .types import (
    DEFAULT_CLIENT_OPTIONS,
    ClientOptions,
    ConnectedCallback,
    ConnectionInfo,
    DisconnectedCallback,
    ErrorCallback,
    JoinMessage,
    ParticipantRole,
    RecoveryConfig,
    RoomInfo,
    RoomState,
    VideoConfig,
    WebRTCConfig,
    WebRTCSignalRequest,
    WebRTCSignalResponse,
    WebRTCStats,
)

logger = logging.getLogger(__name__)


class VideoClientCore:
    """
    Core video client for LeRobot Arena
    Base class providing REST API, WebSocket, and WebRTC functionality
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        options: ClientOptions | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/video"

        # Merge options with defaults
        self.options = DEFAULT_CLIENT_OPTIONS
        if options:
            for key, value in options.__dict__.items():
                if value is not None:
                    setattr(self.options, key, value)

        # Connection state
        self.websocket: websockets.WebSocketServerProtocol | None = None
        self.peer_connection: RTCPeerConnection | None = None
        self.local_stream: Any | None = None
        self.remote_stream: Any | None = None
        self.workspace_id: str | None = None
        self.room_id: str | None = None
        self.role: ParticipantRole | None = None
        self.participant_id: str | None = None
        self.connected = False

        # WebRTC configuration
        self.webrtc_config = WebRTCConfig(
            ice_servers=[{"urls": "stun:stun.l.google.com:19302"}],
            constraints={
                "video": {
                    "width": {"ideal": 640},
                    "height": {"ideal": 480},
                    "frameRate": {"ideal": 30},
                },
                "audio": False,
            },
            bitrate=1000000,
            framerate=30,
            resolution={"width": 640, "height": 480},
            codec_preferences=["VP8", "H264"],
        )
        if self.options.webrtc_config:
            # Merge WebRTC config
            for key, value in self.options.webrtc_config.__dict__.items():
                if value is not None:
                    setattr(self.webrtc_config, key, value)

        # Event callbacks
        self.on_error_callback: ErrorCallback | None = None
        self.on_connected_callback: ConnectedCallback | None = None
        self.on_disconnected_callback: DisconnectedCallback | None = None

        # Background tasks
        self._message_task: asyncio.Task | None = None

    # ============= REST API METHODS =============

    async def list_rooms(self, workspace_id: str) -> list[RoomInfo]:
        """List all available rooms in a workspace"""
        response = await self._fetch_api(f"/workspaces/{workspace_id}/rooms")
        return [self._dict_to_room_info(room) for room in response.get("rooms", [])]

    async def create_room(
        self,
        workspace_id: str | None = None,
        room_id: str | None = None,
        config: VideoConfig | None = None,
        recovery_config: RecoveryConfig | None = None,
    ) -> tuple[str, str]:
        """Create a new room and return (workspace_id, room_id)"""
        # Generate workspace ID if not provided
        final_workspace_id = workspace_id or self._generate_workspace_id()

        payload = {}
        if room_id:
            payload["room_id"] = room_id
        if config:
            payload["config"] = self._video_config_to_dict(config)
        if recovery_config:
            payload["recovery_config"] = self._recovery_config_to_dict(recovery_config)

        response = await self._fetch_api(
            f"/workspaces/{final_workspace_id}/rooms", method="POST", json_data=payload
        )
        return response["workspace_id"], response["room_id"]

    async def delete_room(self, workspace_id: str, room_id: str) -> bool:
        """Delete a room"""
        try:
            response = await self._fetch_api(
                f"/workspaces/{workspace_id}/rooms/{room_id}", method="DELETE"
            )
            return response.get("success", False)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return False
            raise

    async def get_room_state(self, workspace_id: str, room_id: str) -> RoomState:
        """Get current room state"""
        response = await self._fetch_api(
            f"/workspaces/{workspace_id}/rooms/{room_id}/state"
        )
        return self._dict_to_room_state(response["state"])

    async def get_room_info(self, workspace_id: str, room_id: str) -> RoomInfo:
        """Get basic room information"""
        response = await self._fetch_api(f"/workspaces/{workspace_id}/rooms/{room_id}")
        return self._dict_to_room_info(response["room"])

    # ============= WEBRTC SIGNALING =============

    async def send_webrtc_signal(
        self,
        workspace_id: str,
        room_id: str,
        client_id: str,
        message: dict[str, Any] | RTCSessionDescription | RTCIceCandidate,
    ) -> WebRTCSignalResponse:
        """Send WebRTC signaling message"""
        if isinstance(message, RTCSessionDescription):
            message_dict = {"type": message.type, "sdp": message.sdp}
        elif isinstance(message, RTCIceCandidate):
            message_dict = {
                "type": "ice",
                "candidate": message.candidate,
                "sdpMid": message.sdpMid,
                "sdpMLineIndex": message.sdpMLineIndex,
            }
        else:
            message_dict = message

        request = WebRTCSignalRequest(client_id=client_id, message=message_dict)
        response = await self._fetch_api(
            f"/workspaces/{workspace_id}/rooms/{room_id}/webrtc/signal",
            method="POST",
            json_data={"client_id": request.client_id, "message": request.message},
        )
        return WebRTCSignalResponse(**response)

    # ============= WEBSOCKET CONNECTION =============

    async def connect_to_room(
        self,
        workspace_id: str,
        room_id: str,
        role: ParticipantRole,
        participant_id: str | None = None,
    ) -> bool:
        """Connect to a room via WebSocket"""
        if self.connected:
            await self.disconnect()

        self.workspace_id = workspace_id
        self.room_id = room_id
        self.role = role
        self.participant_id = (
            participant_id or f"{role.value}_{int(time.time())}_{id(self) % 10000}"
        )

        # Convert HTTP URL to WebSocket URL
        parsed = urlparse(self.base_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_endpoint = f"{ws_scheme}://{parsed.netloc}/video/workspaces/{workspace_id}/rooms/{room_id}/ws"

        try:
            self.websocket = await websockets.connect(ws_endpoint)

            # Send join message
            await self._send_join_message()

            # Start message handler - this will handle the "joined" response
            self._message_task = asyncio.create_task(self._handle_messages())

            # Wait a brief moment for the join response to be processed
            await asyncio.sleep(0.5)

            # Check if we got connected (will be set by _process_message when "joined" is received)
            if self.connected:
                return True
            await self._cleanup_connection()
            return False

        except Exception as e:
            logger.error(f"Failed to connect to room {room_id}: {e}")
            await self._cleanup_connection()
            return False

    async def disconnect(self) -> None:
        """Disconnect from the current room"""
        await self._cleanup_connection()

        self.workspace_id = None
        self.room_id = None
        self.role = None
        self.participant_id = None
        self.connected = False

        if self.on_disconnected_callback:
            self.on_disconnected_callback()

    # ============= WEBRTC METHODS =============

    def create_peer_connection(self) -> RTCPeerConnection:
        """Create and configure WebRTC peer connection"""
        config = RTCConfiguration(
            iceServers=[
                RTCIceServer(urls=server["urls"])
                for server in self.webrtc_config.ice_servers or []
            ]
        )

        self.peer_connection = RTCPeerConnection(config)

        # Set up event handlers
        self.peer_connection.on(
            "connectionstatechange", self._on_connection_state_change
        )
        self.peer_connection.on(
            "iceconnectionstatechange", self._on_ice_connection_state_change
        )
        self.peer_connection.on("icecandidate", self._on_ice_candidate)
        self.peer_connection.on("track", self._on_track)

        return self.peer_connection

    async def create_offer(self) -> RTCSessionDescription:
        """Create WebRTC offer"""
        if not self.peer_connection:
            raise ValueError("Peer connection not created")

        offer = await self.peer_connection.createOffer()
        await self.peer_connection.setLocalDescription(offer)
        return offer

    async def create_answer(
        self, offer: RTCSessionDescription
    ) -> RTCSessionDescription:
        """Create WebRTC answer"""
        if not self.peer_connection:
            raise ValueError("Peer connection not created")

        await self.peer_connection.setRemoteDescription(offer)
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)
        return answer

    async def set_remote_description(self, description: RTCSessionDescription) -> None:
        """Set remote description"""
        if not self.peer_connection:
            raise ValueError("Peer connection not created")
        await self.peer_connection.setRemoteDescription(description)

    async def add_ice_candidate(self, candidate: RTCIceCandidate) -> None:
        """Add ICE candidate"""
        if not self.peer_connection:
            raise ValueError("Peer connection not created")
        await self.peer_connection.addIceCandidate(candidate)

    # ============= MEDIA METHODS =============

    async def start_producing(self, constraints: dict[str, Any] | None = None) -> Any:
        """Start video production (to be implemented by subclasses)"""
        raise NotImplementedError("start_producing must be implemented by subclasses")

    async def start_screen_share(self) -> Any:
        """Start screen sharing (to be implemented by subclasses)"""
        raise NotImplementedError(
            "start_screen_share must be implemented by subclasses"
        )

    def stop_producing(self) -> None:
        """Stop video production"""
        if self.local_stream:
            # Stop all tracks in the stream
            for track in getattr(self.local_stream, "getTracks", list)():
                track.stop()
            self.local_stream = None

    # ============= GETTERS =============

    def get_local_stream(self) -> Any | None:
        """Get local media stream"""
        return self.local_stream

    def get_remote_stream(self) -> Any | None:
        """Get remote media stream"""
        return self.remote_stream

    def get_peer_connection(self) -> RTCPeerConnection | None:
        """Get WebRTC peer connection"""
        return self.peer_connection

    async def get_stats(self) -> WebRTCStats | None:
        """Get WebRTC statistics"""
        if not self.peer_connection:
            return None

        stats = await self.peer_connection.getStats()
        return self._extract_video_stats(stats)

    # ============= MESSAGE HANDLING =============

    async def _send_join_message(self) -> None:
        """Send join message to server"""
        if not self.websocket or not self.participant_id or not self.role:
            return

        join_message = JoinMessage(participant_id=self.participant_id, role=self.role)

        await self.websocket.send(
            json.dumps({
                "participant_id": join_message.participant_id,
                "role": join_message.role.value,
            })
        )

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.connected = False
            if self.on_disconnected_callback:
                self.on_disconnected_callback()

    async def _process_message(self, data: dict[str, Any]) -> None:
        """Process incoming message based on type"""
        msg_type = data.get("type")

        if msg_type == "joined":
            logger.info(
                f"Successfully joined room {data.get('room_id')} as {data.get('role')}"
            )
            self.connected = True
            if self.on_connected_callback:
                self.on_connected_callback()
        elif msg_type == "heartbeat_ack":
            logger.debug("Heartbeat acknowledged")
        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Server error: {error_msg}")
            if self.on_error_callback:
                self.on_error_callback(error_msg)
        elif msg_type == "participant_joined":
            participant_id = data.get("participant_id", "")
            role = data.get("role", "")
            logger.info(f"Participant joined: {participant_id} as {role}")
            # Forward to role-specific handler
            await self._handle_role_specific_message(data)
        elif msg_type == "participant_left":
            participant_id = data.get("participant_id", "")
            role = data.get("role", "")
            logger.info(f"Participant left: {participant_id} ({role})")
        else:
            # Let subclasses handle specific message types
            await self._handle_role_specific_message(data)

    async def _handle_role_specific_message(self, data: dict[str, Any]) -> None:
        """Handle role-specific messages - to be overridden by subclasses"""

    async def _wait_for_message(
        self, message_type: str, timeout: float = 5.0
    ) -> dict[str, Any] | None:
        """Wait for a specific message type"""
        # For now, just wait briefly and assume success if connected
        # This is a simplified implementation for basic functionality
        await asyncio.sleep(0.5)
        if self.connected:
            return {"type": message_type, "success": True}
        return None

    # ============= UTILITY METHODS =============

    async def send_heartbeat(self) -> None:
        """Send heartbeat to server"""
        if not self.connected or not self.websocket:
            return

        message = {"type": "heartbeat"}
        await self.websocket.send(json.dumps(message))

    def is_connected(self) -> bool:
        """Check if connected to a room"""
        return self.connected

    def get_connection_info(self) -> ConnectionInfo:
        """Get current connection information"""
        return ConnectionInfo(
            connected=self.connected,
            workspace_id=self.workspace_id,
            room_id=self.room_id,
            role=self.role,
            participant_id=self.participant_id,
            base_url=self.base_url,
        )

    # ============= EVENT CALLBACK SETTERS =============

    def on_error(self, callback: ErrorCallback) -> None:
        """Set error callback"""
        self.on_error_callback = callback

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Set connected callback"""
        self.on_connected_callback = callback

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Set disconnected callback"""
        self.on_disconnected_callback = callback

    # ============= WEBRTC EVENT HANDLERS =============

    def _on_connection_state_change(self) -> None:
        """Handle WebRTC connection state change"""
        if self.peer_connection:
            state = self.peer_connection.connectionState
            logger.info(f"🔌 WebRTC connection state: {state}")

            # Handle failed connections for consumers
            if (
                state in ["failed", "disconnected"]
                and self.role == ParticipantRole.CONSUMER
            ):
                logger.warning("⚠️ WebRTC connection failed, attempting to restart...")
                asyncio.create_task(self._handle_connection_failure())

    def _on_ice_connection_state_change(self) -> None:
        """Handle ICE connection state change"""
        if self.peer_connection:
            state = self.peer_connection.iceConnectionState
            logger.info(f"🧊 ICE connection state: {state}")

            # Additional recovery on ICE failure
            if state == "failed" and self.role == ParticipantRole.CONSUMER:
                logger.warning("⚠️ ICE connection failed, will attempt recovery...")
                asyncio.create_task(self._handle_ice_failure())

    def _on_ice_candidate(self, event: Any) -> None:
        """Handle ICE candidate"""
        if event.candidate and self.room_id and self.participant_id:
            # Send ICE candidate via signaling
            asyncio.create_task(self._send_ice_candidate(event.candidate))

    def _on_track(self, track: Any) -> None:
        """Handle received track"""
        logger.info(f"📺 Received track: {track.kind}")
        if track.kind == "video":
            self.remote_stream = track
            # Let subclasses handle track reception
            self._handle_track_received(track)

    def _handle_track_received(self, track: Any) -> None:
        """Handle received track - to be overridden by subclasses"""

    async def _handle_connection_failure(self) -> None:
        """Handle WebRTC connection failure with recovery attempt"""
        if not self.connected or self.role != ParticipantRole.CONSUMER:
            return

        try:
            logger.info("🔄 Attempting WebRTC connection recovery...")

            # Wait a bit before retrying
            await asyncio.sleep(2)

            # Close current peer connection completely
            if self.peer_connection:
                await self.peer_connection.close()
                self.peer_connection = None
                logger.info("🧹 Closed failed peer connection")

            # Reset remote stream
            self.remote_stream = None

            # Reset consumer-specific state if it exists
            if hasattr(self, "has_remote_description"):
                self.has_remote_description = False
            if hasattr(self, "ice_candidate_queue"):
                self.ice_candidate_queue = []
            if hasattr(self, "_last_frame_time"):
                self._last_frame_time = None
            if hasattr(self, "_monitoring_frames"):
                self._monitoring_frames = False

            # Recreate peer connection and restart receiving
            if hasattr(self, "start_receiving"):
                await self.start_receiving()
                logger.info("✅ WebRTC connection recovery completed")
            else:
                logger.warning("⚠️ No start_receiving method available for recovery")

        except Exception as e:
            logger.error(f"❌ Failed to recover WebRTC connection: {e}")
            # Schedule another retry
            await asyncio.sleep(5)
            if self.connected and self.role == ParticipantRole.CONSUMER:
                logger.info("🔄 Scheduling another recovery attempt...")
                asyncio.create_task(self._handle_connection_failure())

    async def _handle_ice_failure(self) -> None:
        """Handle ICE connection failure"""
        # For now, just log - could implement more sophisticated recovery
        logger.warning("🧊 ICE connection failure detected, monitoring for recovery...")
        await asyncio.sleep(5)  # Wait and monitor

        if self.peer_connection and self.peer_connection.iceConnectionState == "failed":
            logger.warning(
                "🔄 ICE still failed after waiting, triggering connection recovery..."
            )
            await self._handle_connection_failure()

    async def _send_ice_candidate(self, candidate: RTCIceCandidate) -> None:
        """Send ICE candidate via signaling"""
        if not self.room_id or not self.participant_id:
            return

        try:
            await self.send_webrtc_signal(
                self.workspace_id,
                self.room_id,
                self.participant_id,
                {
                    "type": "ice",
                    "candidate": candidate.toJSON()
                    if hasattr(candidate, "toJSON")
                    else {
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex,
                    },
                },
            )
        except Exception as e:
            logger.error(f"Failed to send ICE candidate: {e}")

    # ============= PRIVATE HELPERS =============

    async def _fetch_api(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch data from REST API"""
        url = f"{self.api_base}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=self.options.timeout or 5.0)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            kwargs = (
                {"headers": {"Content-Type": "application/json"}} if json_data else {}
            )
            if json_data:
                kwargs["json"] = json_data

            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

    async def _cleanup_connection(self) -> None:
        """Clean up all connections"""
        # Stop message handling task
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None

        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        # Close WebRTC connection
        if self.peer_connection:
            await self.peer_connection.close()
            self.peer_connection = None

        # Stop local streams
        self.stop_producing()
        self.remote_stream = None

    def _extract_video_stats(self, stats: Any) -> WebRTCStats | None:
        """Extract video statistics from WebRTC stats"""
        # This would need to parse the actual stats report
        # For now, return None - implement based on aiortc stats format
        return None

    def _dict_to_room_info(self, data: dict[str, Any]) -> RoomInfo:
        """Convert dictionary to RoomInfo object"""
        # Implementation depends on actual API response format
        # This is a placeholder
        return RoomInfo(
            id=data.get("id", ""),
            participants=data.get("participants", {}),
            frame_count=data.get("frame_count", 0),
            config=VideoConfig(),
            has_producer=data.get("has_producer", False),
            active_consumers=data.get("active_consumers", 0),
        )

    def _dict_to_room_state(self, data: dict[str, Any]) -> RoomState:
        """Convert dictionary to RoomState object"""
        # Implementation depends on actual API response format
        # This is a placeholder
        return RoomState(
            room_id=data.get("room_id", ""),
            participants=data.get("participants", {}),
            frame_count=data.get("frame_count", 0),
            last_frame_time=data.get("last_frame_time"),
            current_config=VideoConfig(),
            timestamp=data.get("timestamp", ""),
        )

    def _video_config_to_dict(self, config: VideoConfig) -> dict[str, Any]:
        """Convert VideoConfig to dictionary"""
        result = {}
        if config.encoding:
            result["encoding"] = config.encoding.value
        if config.resolution:
            result["resolution"] = {
                "width": config.resolution.width,
                "height": config.resolution.height,
            }
        if config.framerate:
            result["framerate"] = config.framerate
        if config.bitrate:
            result["bitrate"] = config.bitrate
        if config.quality:
            result["quality"] = config.quality
        return result

    def _recovery_config_to_dict(self, config: RecoveryConfig) -> dict[str, Any]:
        """Convert RecoveryConfig to dictionary"""
        result = {}
        for key, value in config.__dict__.items():
            if value is not None:
                if hasattr(value, "value"):  # Enum
                    result[key] = value.value
                else:
                    result[key] = value
        return result

    # ============= WORKSPACE HELPERS =============

    def _generate_workspace_id(self) -> str:
        """Generate a UUID-like workspace ID"""
        import uuid

        return str(uuid.uuid4())
