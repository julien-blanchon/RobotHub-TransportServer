#!/usr/bin/env python3
"""
Consumer-First Video Recorder Example

This example demonstrates the "consumer-first" scenario where:
1. Consumer creates a room and waits
2. Producer joins later and starts streaming
3. Consumer records exactly 10 seconds of video when frames arrive
4. Saves the recorded video to disk

This tests the case where consumers are already waiting when producers start streaming.
"""

import asyncio
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from lerobot_arena_client.video import VideoConsumer

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoRecorder:
    """Records video frames for a specific duration"""

    def __init__(
        self,
        duration_seconds: float = 10.0,
        output_dir: str = "./recordings",
        fps: int = 30,
    ):
        self.duration_seconds = duration_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.fps = fps

        # Recording state
        self.recording = False
        self.start_time: float | None = None
        self.frames: list[np.ndarray] = []
        self.frame_count = 0
        self.recording_complete = False

        # Video writer for MP4 output
        self.video_writer: cv2.VideoWriter | None = None
        self.video_path: Path | None = None

    def start_recording(self, width: int, height: int) -> None:
        """Start recording with the given frame dimensions"""
        if self.recording:
            logger.warning("Recording already in progress")
            return

        self.recording = True
        self.start_time = time.time()
        self.frames = []
        self.frame_count = 0
        self.recording_complete = False

        # Create video writer for MP4 output
        timestamp = int(time.time())
        self.video_path = self.output_dir / f"recording_{timestamp}.mp4"

        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(
            str(self.video_path), fourcc, self.fps, (width, height)
        )

        logger.info(f"🎬 Started recording to {self.video_path}")
        logger.info(f"   Duration: {self.duration_seconds}s")
        logger.info(f"   Resolution: {width}x{height}")
        logger.info(f"   Target FPS: {self.fps}")

    def add_frame(self, frame_data) -> bool:
        """Add a frame to the recording. Returns True if recording is complete."""
        if not self.recording or self.recording_complete:
            return self.recording_complete

        # Check if recording duration exceeded
        if self.start_time and time.time() - self.start_time > self.duration_seconds:
            self.stop_recording()
            return True

        try:
            # Extract frame information
            metadata = frame_data.metadata
            width = metadata.get("width", 0)
            height = metadata.get("height", 0)

            # Convert bytes to numpy array (server sends RGB format)
            frame_bytes = frame_data.data
            img_rgb = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((
                height,
                width,
                3,
            ))

            # Convert RGB to BGR for OpenCV
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            # Write frame to video
            if self.video_writer:
                self.video_writer.write(img_bgr)

            # Store frame in memory for backup
            self.frames.append(img_bgr.copy())
            self.frame_count += 1

            # Progress logging
            if self.frame_count % 30 == 0:  # Every ~1 second at 30fps
                elapsed = time.time() - self.start_time if self.start_time else 0
                remaining = max(0, self.duration_seconds - elapsed)
                logger.info(
                    f"🎬 Recording: {elapsed:.1f}s / {self.duration_seconds}s ({remaining:.1f}s remaining)"
                )

        except Exception as e:
            logger.error(f"❌ Error adding frame to recording: {e}")

        return False

    def stop_recording(self) -> dict:
        """Stop recording and save the video"""
        if not self.recording:
            logger.warning("No recording in progress")
            return {}

        self.recording = False
        self.recording_complete = True

        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        # Calculate stats
        end_time = time.time()
        actual_duration = end_time - self.start_time if self.start_time else 0
        actual_fps = self.frame_count / actual_duration if actual_duration > 0 else 0

        stats = {
            "duration": actual_duration,
            "frame_count": self.frame_count,
            "target_fps": self.fps,
            "actual_fps": actual_fps,
            "video_path": str(self.video_path) if self.video_path else None,
            "frame_backup_count": len(self.frames),
        }

        logger.info("🎬 Recording completed!")
        logger.info(f"   Actual duration: {actual_duration:.1f}s")
        logger.info(f"   Frames recorded: {self.frame_count}")
        logger.info(f"   Actual FPS: {actual_fps:.1f}")
        logger.info(f"   Video saved to: {self.video_path}")

        # Also save frame sequence as backup
        if self.frames:
            self._save_frame_sequence()

        return stats

    def _save_frame_sequence(self) -> None:
        """Save individual frames as image sequence backup"""
        frame_dir = self.output_dir / f"frames_{int(time.time())}"
        frame_dir.mkdir(exist_ok=True)

        for i, frame in enumerate(self.frames):
            frame_path = frame_dir / f"frame_{i:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)

        logger.info(f"📸 Saved {len(self.frames)} frames to {frame_dir}")


async def main():
    """Main consumer-first recorder example"""
    # Configuration
    base_url = "http://localhost:8000"
    recording_duration = 10.0  # Record for 10 seconds

    logger.info("🎬 Consumer-First Video Recorder")
    logger.info("=" * 50)
    logger.info(f"Server: {base_url}")
    logger.info(f"Recording duration: {recording_duration}s")
    logger.info("")

    # Create consumer
    consumer = VideoConsumer(base_url)
    recorder = VideoRecorder(duration_seconds=recording_duration)

    # Track recording state
    recording_started = False
    recording_stats = {}

    def handle_frame(frame_data):
        """Handle received frame data"""
        nonlocal recording_started, recording_stats

        if not recording_started:
            # Start recording on first frame
            metadata = frame_data.metadata
            width = metadata.get("width", 640)
            height = metadata.get("height", 480)

            recorder.start_recording(width, height)
            recording_started = True

        # Add frame to recording
        is_complete = recorder.add_frame(frame_data)

        if is_complete and not recording_stats:
            recording_stats = recorder.stop_recording()

    # Set up event handlers
    consumer.on_frame_update(handle_frame)

    def on_stream_started(config, producer_id):
        logger.info(f"🚀 Producer {producer_id} started streaming!")
        logger.info("🎬 Ready to record when frames arrive...")

    def on_stream_stopped(producer_id, reason):
        logger.info(f"⏹️ Producer {producer_id} stopped streaming")
        if reason:
            logger.info(f"   Reason: {reason}")

    consumer.on_stream_started(on_stream_started)
    consumer.on_stream_stopped(on_stream_stopped)

    try:
        # Step 1: Create our own room
        logger.info("🏗️ Creating video room...")
        room_id = await consumer.create_room("consumer-first-test")
        logger.info(f"✅ Created room: {room_id}")

        # Step 2: Connect as consumer
        logger.info("🔌 Connecting to room as consumer...")
        connected = await consumer.connect(room_id)

        if not connected:
            logger.error("❌ Failed to connect to room")
            return

        logger.info("✅ Connected as consumer successfully")

        # Step 3: Start receiving (prepare for video)
        logger.info("📺 Starting video reception...")
        await consumer.start_receiving()

        # Step 4: Wait for producer and record
        logger.info("⏳ Waiting for producer to join and start streaming...")
        logger.info(f"   Room ID: {room_id}")
        logger.info("   (Start a producer with this room ID to begin recording)")

        # Wait for recording to complete or timeout
        timeout = 300  # 5 minutes timeout
        start_wait = time.time()

        while time.time() - start_wait < timeout:
            await asyncio.sleep(1)

            # Check if recording is complete
            if recording_stats:
                logger.info("🎉 Recording completed successfully!")
                break

            # Show waiting status every 30 seconds
            elapsed_wait = time.time() - start_wait
            if int(elapsed_wait) % 30 == 0 and elapsed_wait > 0:
                remaining_timeout = timeout - elapsed_wait
                logger.info(
                    f"⏳ Still waiting for producer... ({remaining_timeout:.0f}s timeout remaining)"
                )

        # Final results
        if recording_stats:
            logger.info("📊 Final Recording Results:")
            logger.info(f"   Duration: {recording_stats['duration']:.1f}s")
            logger.info(f"   Frames: {recording_stats['frame_count']}")
            logger.info(f"   FPS: {recording_stats['actual_fps']:.1f}")
            logger.info(f"   Video file: {recording_stats['video_path']}")
            logger.info("🎉 SUCCESS: Consumer-first recording completed!")
        else:
            logger.warning("⚠️ No recording was made - producer may not have joined")

    except Exception as e:
        logger.error(f"❌ Consumer-first recorder failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")
        try:
            await consumer.stop_receiving()
            await consumer.disconnect()
            logger.info("👋 Consumer disconnected successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        import traceback

        traceback.print_exc()
