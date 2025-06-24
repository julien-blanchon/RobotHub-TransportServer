#!/usr/bin/env python3
"""
Test Consumer Fix

This script tests the fixed Python video consumer to ensure it can properly
receive and decode video frames from the server.
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


class FrameProcessor:
    """Processes received video frames and saves them for verification"""

    def __init__(self, output_dir: str = "./test_frames"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.frame_count = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.last_frame_time = time.time()

    def process_frame(self, frame_data):
        """Process received frame data"""
        try:
            self.frame_count += 1
            current_time = time.time()

            # Extract metadata
            metadata = frame_data.metadata
            width = metadata.get("width", 0)
            height = metadata.get("height", 0)
            format_type = metadata.get("format", "unknown")

            # Convert bytes back to numpy array
            frame_bytes = frame_data.data
            self.total_bytes += len(frame_bytes)

            # Reconstruct numpy array from bytes
            img = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3))

            # Save every 10th frame for verification
            if self.frame_count % 10 == 0:
                # Convert RGB to BGR for OpenCV saving
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                frame_path = self.output_dir / f"frame_{self.frame_count:06d}.jpg"
                cv2.imwrite(str(frame_path), img_bgr)
                logger.info(f"💾 Saved frame {self.frame_count} to {frame_path}")

            # Calculate FPS
            fps = (
                1.0 / (current_time - self.last_frame_time)
                if self.frame_count > 1
                else 0
            )
            self.last_frame_time = current_time

            # Log progress every 30 frames
            if self.frame_count % 30 == 0:
                elapsed = current_time - self.start_time
                avg_fps = self.frame_count / elapsed if elapsed > 0 else 0
                mb_received = self.total_bytes / (1024 * 1024)

                logger.info("📊 Frame Stats:")
                logger.info(f"   Frames: {self.frame_count}")
                logger.info(f"   Resolution: {width}x{height}")
                logger.info(f"   Format: {format_type}")
                logger.info(f"   Current FPS: {fps:.1f}")
                logger.info(f"   Average FPS: {avg_fps:.1f}")
                logger.info(f"   Data received: {mb_received:.2f} MB")

        except Exception as e:
            logger.error(f"❌ Error processing frame {self.frame_count}: {e}")


async def test_consumer_fix():
    """Test the fixed consumer implementation"""
    # Connect to the "webcam" room mentioned in the conversation
    room_id = "webcam"
    base_url = "http://localhost:8000"

    logger.info("🎬 Testing Fixed Video Consumer")
    logger.info("=" * 50)
    logger.info(f"Room ID: {room_id}")
    logger.info(f"Server: {base_url}")

    # Create frame processor
    processor = FrameProcessor()

    # Create consumer
    consumer = VideoConsumer(base_url)

    # Set up frame callback
    consumer.on_frame_update(processor.process_frame)

    # Track connection states
    connection_established = False
    frames_received = False

    def on_track_received(track):
        nonlocal connection_established
        connection_established = True
        logger.info(f"✅ Video track received: {track.kind}")

    try:
        logger.info("🔌 Connecting to room...")
        connected = await consumer.connect(room_id)

        if not connected:
            logger.error("❌ Failed to connect to room")
            return False

        logger.info("✅ Connected to room successfully")

        # Start receiving
        logger.info("📺 Starting video reception...")
        await consumer.start_receiving()

        # Wait for frames with timeout
        test_duration = 30  # 30 seconds
        logger.info(f"⏱️ Testing for {test_duration} seconds...")

        start_time = time.time()
        while time.time() - start_time < test_duration:
            await asyncio.sleep(1)

            # Check if we're receiving frames
            if processor.frame_count > 0 and not frames_received:
                frames_received = True
                logger.info("🎉 First frame received successfully!")

            # Show periodic status
            if int(time.time() - start_time) % 5 == 0:
                elapsed = time.time() - start_time
                logger.info(
                    f"⏱️ Test progress: {elapsed:.0f}s - Frames: {processor.frame_count}"
                )

        # Final results
        logger.info("📊 Test Results:")
        logger.info(f"   Connection established: {connection_established}")
        logger.info(f"   Frames received: {frames_received}")
        logger.info(f"   Total frames: {processor.frame_count}")

        if processor.frame_count > 0:
            elapsed = time.time() - processor.start_time
            avg_fps = processor.frame_count / elapsed
            mb_total = processor.total_bytes / (1024 * 1024)

            logger.info(f"   Average FPS: {avg_fps:.1f}")
            logger.info(f"   Total data: {mb_total:.2f} MB")
            logger.info(
                f"   Saved frames: {len(list(processor.output_dir.glob('*.jpg')))}"
            )

            # Verify saved frames
            saved_frames = list(processor.output_dir.glob("*.jpg"))
            if saved_frames:
                logger.info(f"✅ SUCCESS: Frames saved to {processor.output_dir}")
                logger.info(f"   Example frame: {saved_frames[0]}")

            return True
        logger.error("❌ FAILED: No frames received")
        return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")
        await consumer.stop_receiving()
        logger.info("👋 Test completed")


async def main():
    """Main test function"""
    try:
        success = await test_consumer_fix()
        if success:
            logger.info("🎉 Consumer fix test PASSED!")
            return 0
        logger.error("💥 Consumer fix test FAILED!")
        return 1
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
