#!/usr/bin/env python3
"""
Video Consumer Example - Fixed Version

This example demonstrates how to connect as a video consumer and receive
video frames from a producer in the LeRobot Arena.
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


class VideoFrameHandler:
    """Handles received video frames with optional saving and display"""

    def __init__(
        self, save_frames: bool = False, output_dir: str = "./received_frames"
    ):
        self.save_frames = save_frames
        self.output_dir = Path(output_dir) if save_frames else None
        if self.output_dir:
            self.output_dir.mkdir(exist_ok=True)

        self.frame_count = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.last_log_time = time.time()

    def handle_frame(self, frame_data):
        """Process received frame data"""
        try:
            self.frame_count += 1
            current_time = time.time()

            # Extract frame information
            metadata = frame_data.metadata
            width = metadata.get("width", 0)
            height = metadata.get("height", 0)
            format_type = metadata.get("format", "unknown")

            # Convert bytes to numpy array
            frame_bytes = frame_data.data
            self.total_bytes += len(frame_bytes)

            # Reconstruct image from bytes (server sends RGB format)
            img = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3))

            # Save frames if requested
            if self.save_frames and self.frame_count % 30 == 0:  # Save every 30th frame
                # Convert RGB to BGR for OpenCV
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                frame_path = self.output_dir / f"frame_{self.frame_count:06d}.jpg"
                cv2.imwrite(str(frame_path), img_bgr)
                logger.info(f"💾 Saved frame {self.frame_count} to {frame_path}")

            # Log statistics periodically
            if current_time - self.last_log_time >= 5.0:  # Every 5 seconds
                elapsed = current_time - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                mb_received = self.total_bytes / (1024 * 1024)

                logger.info("📊 Video Stats:")
                logger.info(f"   Frames received: {self.frame_count}")
                logger.info(f"   Resolution: {width}x{height}")
                logger.info(f"   Format: {format_type}")
                logger.info(f"   Average FPS: {fps:.1f}")
                logger.info(f"   Data received: {mb_received:.2f} MB")

                self.last_log_time = current_time

        except Exception as e:
            logger.error(f"❌ Error handling frame {self.frame_count}: {e}")


async def main():
    """Main consumer example"""
    # Configuration
    room_id = "webcam"  # Use the test webcam room
    base_url = "http://localhost:8000"
    duration = 60  # Run for 60 seconds
    save_frames = True  # Save some frames as proof

    logger.info("🎬 Video Consumer Example - Fixed Version")
    logger.info("=" * 50)
    logger.info(f"Room ID: {room_id}")
    logger.info(f"Server: {base_url}")
    logger.info(f"Duration: {duration} seconds")
    logger.info(f"Save frames: {save_frames}")

    # Create frame handler
    frame_handler = VideoFrameHandler(save_frames=save_frames)

    # Create consumer
    consumer = VideoConsumer(base_url)

    # Set up event handlers
    consumer.on_frame_update(frame_handler.handle_frame)

    # Track connection progress
    connection_events = []

    try:
        logger.info("🔌 Connecting to room...")
        connected = await consumer.connect(room_id)

        if not connected:
            logger.error("❌ Failed to connect to room")
            return

        logger.info("✅ Connected to room successfully")
        connection_events.append("connected")

        # Start receiving video
        logger.info("📺 Starting video reception...")
        await consumer.start_receiving()
        connection_events.append("receiving_started")

        # Run for specified duration
        logger.info(f"⏱️ Running for {duration} seconds...")
        logger.info("📺 Waiting for video frames... (Press Ctrl+C to stop early)")

        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                await asyncio.sleep(1)

                # Show progress
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0 and elapsed > 0:  # Every 10 seconds
                    logger.info(
                        f"⏱️ Progress: {elapsed:.0f}s - Frames: {frame_handler.frame_count}"
                    )

        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user")

        # Final statistics
        elapsed = time.time() - start_time
        logger.info("📊 Final Results:")
        logger.info(f"   Test duration: {elapsed:.1f} seconds")
        logger.info(f"   Total frames: {frame_handler.frame_count}")
        logger.info(f"   Connection events: {connection_events}")

        if frame_handler.frame_count > 0:
            avg_fps = frame_handler.frame_count / elapsed
            mb_total = frame_handler.total_bytes / (1024 * 1024)

            logger.info(f"   Average FPS: {avg_fps:.1f}")
            logger.info(f"   Total data: {mb_total:.2f} MB")

            if save_frames and frame_handler.output_dir:
                saved_files = list(frame_handler.output_dir.glob("*.jpg"))
                logger.info(f"   Saved frames: {len(saved_files)}")
                if saved_files:
                    logger.info(f"   Output directory: {frame_handler.output_dir}")

            logger.info("🎉 SUCCESS: Video consumer is working correctly!")
        else:
            logger.warning("⚠️ No frames received - check if producer is active")

    except Exception as e:
        logger.error(f"❌ Consumer example failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")
        try:
            await consumer.stop_receiving()
            logger.info("👋 Consumer stopped successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        import traceback

        traceback.print_exc()
