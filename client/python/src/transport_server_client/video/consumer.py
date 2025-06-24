"""
Consumer client for receiving video streams in LeRobot Arena
"""

import asyncio
import logging
from typing import Any

from aiortc import RTCIceCandidate, RTCSessionDescription

from .core import VideoClientCore
from .types import (
    ClientOptions,
    FrameData,
    FrameUpdateCallback,
    ParticipantRole,
    RecoveryTriggeredCallback,
    StatusUpdateCallback,
    StreamStartedCallback,
    StreamStatsCallback,
    StreamStoppedCallback,
    VideoConfig,
    VideoConfigUpdateCallback,
    WebRTCStats,
)

logger = logging.getLogger(__name__)


class VideoConsumer(VideoClientCore):
    """Consumer client for receiving video streams in LeRobot Arena"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        options: ClientOptions | None = None,
    ):
        super().__init__(base_url, options)

        # Event callbacks
        self.on_frame_update_callback: FrameUpdateCallback | None = None
        self.on_video_config_update_callback: VideoConfigUpdateCallback | None = None
        self.on_stream_started_callback: StreamStartedCallback | None = None
        self.on_stream_stopped_callback: StreamStoppedCallback | None = None
        self.on_recovery_triggered_callback: RecoveryTriggeredCallback | None = None
        self.on_status_update_callback: StatusUpdateCallback | None = None
        self.on_stream_stats_callback: StreamStatsCallback | None = None

        # ICE candidate queuing for proper timing
        self.ice_candidate_queue: list[dict[str, Any]] = []
        self.has_remote_description = False

        # Frame monitoring for stream health
        self._last_frame_time: float | None = None
        self._frame_timeout_task: asyncio.Task | None = None
        self._monitoring_frames = False

    # ============= CONSUMER CONNECTION =============

    async def connect(
        self, workspace_id: str, room_id: str, participant_id: str | None = None
    ) -> bool:
        """Connect to a room as consumer"""
        # Create peer connection BEFORE connecting to avoid race condition
        logger.info("Creating peer connection for consumer...")
        self.create_peer_connection()

        # Add transceiver to receive video
        if self.peer_connection:
            self.peer_connection.addTransceiver("video", direction="recvonly")
            logger.info("Added video transceiver for consumer")

        # Now connect to room - we're ready for WebRTC offers
        connected = await self.connect_to_room(
            workspace_id, room_id, ParticipantRole.CONSUMER, participant_id
        )

        if connected:
            # Create peer connection immediately so we're ready for WebRTC offers
            logger.info("🔧 Consumer connected and ready for WebRTC offers")
            await self.start_receiving()

        return connected

    # ============= CONSUMER METHODS =============

    async def start_receiving(self) -> None:
        """Start receiving video stream"""
        if not self.connected:
            raise ValueError("Must be connected to start receiving")

        # Reset WebRTC state
        self.has_remote_description = False
        self.ice_candidate_queue = []

        # Create peer connection for receiving (if not already created)
        if not self.peer_connection:
            self.create_peer_connection()

            # Set up to receive remote stream
            if self.peer_connection:
                # Add transceiver to receive video
                self.peer_connection.addTransceiver("video", direction="recvonly")
                logger.info("Added video transceiver for consumer")
        else:
            logger.info("Peer connection already exists for consumer")

    async def stop_receiving(self) -> None:
        """Stop receiving video stream"""
        # Stop frame monitoring
        self._monitoring_frames = False
        if self._frame_timeout_task and not self._frame_timeout_task.done():
            self._frame_timeout_task.cancel()

        if self.peer_connection:
            await self.peer_connection.close()
            self.peer_connection = None
        self.remote_stream = None

    # ============= WEBRTC NEGOTIATION =============

    async def handle_webrtc_offer(
        self, offer_data: dict[str, Any], from_producer: str
    ) -> None:
        """Handle WebRTC offer from producer"""
        try:
            logger.info(f"📥 Received WebRTC offer from producer {from_producer}")

            # Check if we need to restart the connection (new offer from same producer)
            if self.peer_connection and self.has_remote_description:
                logger.info("🔄 Restarting connection for new stream...")
                await self._restart_connection_for_new_stream()

            if not self.peer_connection:
                logger.info("🔧 Creating new peer connection for offer...")
                self.create_peer_connection()

                # Add transceiver to receive video
                if self.peer_connection:
                    self.peer_connection.addTransceiver("video", direction="recvonly")
                    logger.info("Added video transceiver for new connection")

            # Reset state for new offer
            self.has_remote_description = False
            self.ice_candidate_queue = []

            # Set remote description (the offer)
            offer = RTCSessionDescription(
                sdp=offer_data["sdp"], type=offer_data["type"]
            )
            await self.set_remote_description(offer)
            self.has_remote_description = True

            # Process any queued ICE candidates now that we have remote description
            await self._process_queued_ice_candidates()

            # Create answer
            answer = await self.create_answer(offer)

            logger.info(f"📤 Sending WebRTC answer to producer {from_producer}")

            # Send answer back through server to producer
            if self.workspace_id and self.room_id and self.participant_id:
                await self.send_webrtc_signal(
                    self.workspace_id,
                    self.room_id,
                    self.participant_id,
                    {
                        "type": "answer",
                        "sdp": answer.sdp,
                        "target_producer": from_producer,
                    },
                )

            logger.info("✅ WebRTC negotiation completed from consumer side")
        except Exception as e:
            logger.error(f"Failed to handle WebRTC offer: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"Failed to handle WebRTC offer: {e}")

    async def _restart_connection_for_new_stream(self) -> None:
        """Restart connection for new stream (called when getting new offer)"""
        try:
            logger.info("🔄 Restarting peer connection for new stream...")

            # Stop frame monitoring
            self._monitoring_frames = False
            if self._frame_timeout_task and not self._frame_timeout_task.done():
                self._frame_timeout_task.cancel()

            # Close existing peer connection
            if self.peer_connection:
                await self.peer_connection.close()
                self.peer_connection = None

            # Reset all WebRTC state
            self.remote_stream = None
            self.has_remote_description = False
            self.ice_candidate_queue = []
            self._last_frame_time = None

            logger.info("✅ Connection restart completed")

        except Exception as e:
            logger.error(f"❌ Error restarting connection: {e}")
            # Continue anyway - we'll try to create a new connection

    async def handle_webrtc_ice(
        self, ice_data: dict[str, Any], from_producer: str
    ) -> None:
        """Handle WebRTC ICE candidate from producer"""
        if not self.peer_connection:
            logger.warning("No peer connection available to handle ICE")
            return

        try:
            logger.info(f"📥 Received WebRTC ICE from producer {from_producer}")

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

            if not self.has_remote_description:
                # Queue ICE candidate until we have remote description
                logger.info(
                    f"🔄 Queuing ICE candidate from {from_producer} (no remote description yet)"
                )
                self.ice_candidate_queue.append({
                    "candidate": candidate,
                    "from_producer": from_producer,
                })
                return

            # Add ICE candidate to peer connection
            await self.add_ice_candidate(candidate)

            logger.info(f"✅ WebRTC ICE handled from producer {from_producer}")
        except Exception as e:
            logger.error(f"Failed to handle WebRTC ICE from {from_producer}: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"Failed to handle WebRTC ICE: {e}")

    async def _process_queued_ice_candidates(self) -> None:
        """Process all queued ICE candidates after remote description is set"""
        if not self.ice_candidate_queue:
            return

        logger.info(
            f"🔄 Processing {len(self.ice_candidate_queue)} queued ICE candidates"
        )

        for item in self.ice_candidate_queue:
            try:
                candidate = item["candidate"]
                from_producer = item["from_producer"]

                if self.peer_connection:
                    await self.peer_connection.addIceCandidate(candidate)
                    logger.info(
                        f"✅ Processed queued ICE candidate from {from_producer}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to process queued ICE candidate from {item.get('from_producer', 'unknown')}: {e}"
                )

        # Clear the queue
        self.ice_candidate_queue = []

    # ============= EVENT CALLBACKS =============

    def on_frame_update(self, callback: FrameUpdateCallback) -> None:
        """Set callback for frame updates"""
        self.on_frame_update_callback = callback

    def on_video_config_update(self, callback: VideoConfigUpdateCallback) -> None:
        """Set callback for video config updates"""
        self.on_video_config_update_callback = callback

    def on_stream_started(self, callback: StreamStartedCallback) -> None:
        """Set callback for stream started events"""
        self.on_stream_started_callback = callback

    def on_stream_stopped(self, callback: StreamStoppedCallback) -> None:
        """Set callback for stream stopped events"""
        self.on_stream_stopped_callback = callback

    def on_recovery_triggered(self, callback: RecoveryTriggeredCallback) -> None:
        """Set callback for recovery triggered events"""
        self.on_recovery_triggered_callback = callback

    def on_status_update(self, callback: StatusUpdateCallback) -> None:
        """Set callback for status updates"""
        self.on_status_update_callback = callback

    def on_stream_stats(self, callback: StreamStatsCallback) -> None:
        """Set callback for stream statistics"""
        self.on_stream_stats_callback = callback

    # ============= MESSAGE HANDLING =============

    async def _handle_role_specific_message(self, data: dict[str, Any]) -> None:
        """Handle consumer-specific messages"""
        msg_type = data.get("type")

        if msg_type == "frame_update":
            await self._handle_frame_update(data)
        elif msg_type == "video_config_update":
            await self._handle_video_config_update(data)
        elif msg_type == "stream_started":
            await self._handle_stream_started(data)
        elif msg_type == "stream_stopped":
            await self._handle_stream_stopped(data)
        elif msg_type == "recovery_triggered":
            await self._handle_recovery_triggered(data)
        elif msg_type == "status_update":
            await self._handle_status_update(data)
        elif msg_type == "stream_stats":
            await self._handle_stream_stats(data)
        elif msg_type == "participant_joined":
            logger.info(
                f"📥 Participant joined: {data.get('participant_id')} as {data.get('role')}"
            )
            # If it's a producer joining, we should be ready for offers
            if data.get("role") == "producer":
                producer_id = data.get("participant_id", "")
                logger.info(
                    f"🎬 Producer {producer_id} joined - ready for WebRTC offers"
                )
        elif msg_type == "participant_left":
            logger.info(
                f"📤 Participant left: {data.get('participant_id')} ({data.get('role')})"
            )
            # If it's a producer leaving, we should be ready for recovery
            if data.get("role") == "producer":
                producer_id = data.get("participant_id", "")
                logger.info(
                    f"👋 Producer {producer_id} left - waiting for reconnection..."
                )
                # Reset state for potential reconnection
                self.has_remote_description = False
                self.ice_candidate_queue = []
        elif msg_type == "webrtc_offer":
            await self.handle_webrtc_offer(
                data.get("offer", {}), data.get("from_producer", "")
            )
        elif msg_type == "webrtc_answer":
            logger.info("Received WebRTC answer (consumer should not receive this)")
        elif msg_type == "webrtc_ice":
            await self.handle_webrtc_ice(
                data.get("candidate", {}), data.get("from_producer", "")
            )
        elif msg_type == "emergency_stop":
            logger.warning(f"Emergency stop: {data.get('reason', 'Unknown reason')}")
            if self.on_error_callback:
                self.on_error_callback(
                    f"Emergency stop: {data.get('reason', 'Unknown reason')}"
                )
        else:
            logger.warning(f"Unknown message type for consumer: {msg_type}")

    async def _handle_frame_update(self, data: dict[str, Any]) -> None:
        """Handle frame update message"""
        if self.on_frame_update_callback:
            frame_data = FrameData(
                data=data.get("data", b""), metadata=data.get("metadata", {})
            )
            self.on_frame_update_callback(frame_data)

    async def _handle_video_config_update(self, data: dict[str, Any]) -> None:
        """Handle video config update message"""
        if self.on_video_config_update_callback:
            config = self._dict_to_video_config(data.get("config", {}))
            self.on_video_config_update_callback(config)

    async def _handle_stream_started(self, data: dict[str, Any]) -> None:
        """Handle stream started message"""
        if self.on_stream_started_callback:
            config = self._dict_to_video_config(data.get("config", {}))
            participant_id = data.get("participant_id", "")
            self.on_stream_started_callback(config, participant_id)

        logger.info(
            f"🚀 Stream started by producer {data.get('participant_id')}, ready to receive video"
        )

    async def _handle_stream_stopped(self, data: dict[str, Any]) -> None:
        """Handle stream stopped message"""
        producer_id = data.get("participant_id", "")
        reason = data.get("reason")

        logger.info(f"⏹️ Stream stopped by producer {producer_id}")
        if reason:
            logger.info(f"   Reason: {reason}")

        # Reset WebRTC state for potential restart
        self.has_remote_description = False
        self.ice_candidate_queue = []

        # Keep peer connection alive for potential restart
        logger.info("🔄 Ready for stream restart...")

        if self.on_stream_stopped_callback:
            self.on_stream_stopped_callback(producer_id, reason)

    async def _handle_recovery_triggered(self, data: dict[str, Any]) -> None:
        """Handle recovery triggered message"""
        if self.on_recovery_triggered_callback:
            from .types import RecoveryPolicy

            policy = RecoveryPolicy(data.get("policy", "freeze_last_frame"))
            reason = data.get("reason", "")
            self.on_recovery_triggered_callback(policy, reason)

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

    # ============= TRACK HANDLING =============

    def _handle_track_received(self, track: Any) -> None:
        """Handle received video track"""
        logger.info(f"📺 Received video track: {track.kind}")
        self.remote_stream = track

        # Start reading frames from the track
        if track.kind == "video":
            asyncio.create_task(self._read_video_frames(track))
            # Start frame monitoring
            asyncio.create_task(self._start_frame_monitoring())

    async def _read_video_frames(self, track: Any) -> None:
        """Read frames from video track and trigger callbacks"""
        frame_count = 0
        self._monitoring_frames = True
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            logger.info(f"📹 Starting frame reading from track: {track.kind}")

            while self._monitoring_frames:
                try:
                    # Use timeout to detect stream issues
                    frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                    frame_count += 1
                    consecutive_errors = 0  # Reset error count on success

                    # Update frame monitoring
                    import time

                    self._last_frame_time = time.time()

                    # Convert frame to numpy array properly - use RGB format to match server
                    img = frame.to_ndarray(format="rgb24")

                    # Convert RGB to BGR for OpenCV compatibility if needed
                    # For callbacks, we can provide RGB data and let user decide format
                    frame_data = FrameData(
                        data=img.tobytes(),
                        metadata={
                            "width": frame.width,
                            "height": frame.height,
                            "format": "rgb24",  # Server sends RGB format
                            "pts": frame.pts,
                            "time_base": str(frame.time_base),
                            "frame_count": frame_count,
                        },
                    )

                    # Trigger frame update callback
                    if self.on_frame_update_callback:
                        self.on_frame_update_callback(frame_data)

                    if frame_count % 30 == 0:  # Log every 30 frames
                        logger.info(f"📹 Processed {frame_count} video frames")

                except TimeoutError:
                    logger.warning(
                        "⏰ Timeout waiting for video frame - stream may have stopped"
                    )
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(
                            "❌ Too many consecutive frame timeouts - stopping frame reading"
                        )
                        break
                    await asyncio.sleep(1)  # Wait before retrying
                    continue

                except Exception as frame_error:
                    # Individual frame processing error - log but continue
                    consecutive_errors += 1
                    logger.warning(
                        f"⚠️ Error processing frame {frame_count}: {frame_error}"
                    )

                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(
                            f"❌ Too many consecutive frame errors ({consecutive_errors}) - stopping frame reading"
                        )
                        break

                    await asyncio.sleep(0.1)  # Brief pause before retrying
                    continue

        except Exception as e:
            logger.error(f"❌ Fatal error in frame reading loop: {e}")

        finally:
            logger.info(
                f"📊 Frame reading stopped. Total frames processed: {frame_count}"
            )
            self._monitoring_frames = False

            # If we stopped due to errors and we're still connected, try to restart
            if consecutive_errors >= max_consecutive_errors and self.connected:
                logger.info(
                    "🔄 Frame reading stopped due to errors - triggering connection recovery"
                )
                asyncio.create_task(self._handle_connection_failure())

    async def _start_frame_monitoring(self) -> None:
        """Start monitoring for frame timeouts"""
        if self._frame_timeout_task and not self._frame_timeout_task.done():
            self._frame_timeout_task.cancel()

        self._frame_timeout_task = asyncio.create_task(self._monitor_frame_timeout())

    async def _monitor_frame_timeout(self) -> None:
        """Monitor for frame timeouts and trigger recovery if needed"""
        timeout_seconds = 10.0  # No frames for 10 seconds = problem

        while self.connected and self._monitoring_frames:
            await asyncio.sleep(5)  # Check every 5 seconds

            if self._last_frame_time is not None:
                import time

                time_since_last_frame = time.time() - self._last_frame_time

                if time_since_last_frame > timeout_seconds:
                    logger.warning(
                        f"⚠️ No frames received for {time_since_last_frame:.1f}s - stream may be stopped"
                    )
                    # Reset frame monitoring
                    self._last_frame_time = None

    # ============= UTILITY METHODS =============

    @staticmethod
    async def create_and_connect(
        workspace_id: str,
        room_id: str,
        base_url: str = "http://localhost:8000",
        participant_id: str | None = None,
    ) -> "VideoConsumer":
        """Create a consumer and automatically connect to a room"""
        consumer = VideoConsumer(base_url)
        connected = await consumer.connect(workspace_id, room_id, participant_id)

        if not connected:
            raise ValueError("Failed to connect as video consumer")

        return consumer

    def attach_to_video_element(self, video_element: Any) -> None:
        """Attach remote stream to a video element (for web frameworks)"""
        if self.remote_stream:
            # This would be used in web contexts
            # For now, just log that we have a stream
            logger.info("Video stream available for attachment")

    async def get_video_stats(self) -> WebRTCStats | None:
        """Get current video statistics"""
        return await self.get_stats()

    def _dict_to_video_config(self, data: dict[str, Any]) -> VideoConfig:
        """Convert dictionary to VideoConfig"""
        from .types import Resolution, VideoEncoding

        config = VideoConfig()

        if "encoding" in data:
            config.encoding = VideoEncoding(data["encoding"])

        if "resolution" in data:
            res_data = data["resolution"]
            config.resolution = Resolution(
                width=res_data.get("width", 640), height=res_data.get("height", 480)
            )

        if "framerate" in data:
            config.framerate = data["framerate"]

        if "bitrate" in data:
            config.bitrate = data["bitrate"]

        if "quality" in data:
            config.quality = data["quality"]

        return config
