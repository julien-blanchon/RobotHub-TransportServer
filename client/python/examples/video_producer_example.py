#!/usr/bin/env python3
"""
Basic Video Producer Example

Demonstrates how to use the LeRobot Arena Python video client for streaming.
This example creates animated video content and streams it to the arena server.
"""

import asyncio
import logging
import time

import numpy as np

# Import the video client
from lerobot_arena_client.video import (
    VideoProducer,
    create_producer_client,
)


async def animated_frame_source() -> np.ndarray | None:
    """Create animated frames with colorful patterns"""
    # Create a colorful animated frame
    height, width = 480, 640
    frame_count = int(time.time() * 30) % 1000  # 30 fps simulation

    # Generate animated RGB channels using vectorized operations
    time_factor = frame_count * 0.1

    # Create colorful animated patterns
    y_coords, x_coords = np.meshgrid(np.arange(width), np.arange(height), indexing="xy")

    r = (128 + 127 * np.sin(time_factor + x_coords * 0.01)).astype(np.uint8)
    g = (128 + 127 * np.sin(time_factor + y_coords * 0.01)).astype(np.uint8)
    b = (128 + 127 * np.sin(time_factor) * np.ones((height, width))).astype(np.uint8)

    # Stack into RGB frame
    frame = np.stack([r, g, b], axis=2)

    # Add a moving circle for visual feedback
    center_x = int(320 + 200 * np.sin(frame_count * 0.05))
    center_y = int(240 + 100 * np.cos(frame_count * 0.05))

    # Create circle mask
    circle_mask = (x_coords - center_x) ** 2 + (y_coords - center_y) ** 2 < 50**2
    frame[circle_mask] = [255, 255, 0]  # Yellow circle

    # Add frame counter text overlay
    import cv2

    cv2.putText(
        frame,
        f"Frame {frame_count}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 0),
        3,
    )  # Black outline
    cv2.putText(
        frame,
        f"Frame {frame_count}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (255, 255, 255),
        2,
    )  # White text

    return frame


async def main():
    """Main function demonstrating video producer functionality"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting LeRobot Arena Video Producer Example")

    try:
        # Create video producer with configuration
        producer = VideoProducer(base_url="http://localhost:8000")

        # Set up event handlers
        producer.on_connected(lambda: logger.info("✅ Connected to video server"))
        producer.on_disconnected(
            lambda: logger.info("👋 Disconnected from video server")
        )
        producer.on_error(lambda error: logger.error(f"❌ Error: {error}"))

        producer.on_status_update(
            lambda status, data: logger.info(f"📊 Status: {status}")
        )
        producer.on_stream_stats(
            lambda stats: logger.debug(f"📈 Stats: {stats.average_fps:.1f}fps")
        )

        # Create a room and connect
        room_id = await producer.create_room()
        logger.info(f"🏠 Created room: {room_id}")

        connected = await producer.connect(room_id)
        if not connected:
            logger.error("❌ Failed to connect to room")
            return

        logger.info(f"✅ Connected as producer to room: {room_id}")

        # Start custom video stream with animated content
        logger.info("🎬 Starting animated video stream...")
        await producer.start_custom_stream(animated_frame_source)

        logger.info("📺 Video streaming started!")
        logger.info(f"🔗 Consumers can connect to room: {room_id}")
        logger.info(
            f"📱 Use JS consumer: http://localhost:5173/consumer?room={room_id}"
        )

        # Stream for demo duration
        duration = 30  # Stream for 30 seconds
        logger.info(f"⏱️  Streaming for {duration} seconds...")

        for i in range(duration):
            await asyncio.sleep(1)
            if i % 5 == 0:
                logger.info(f"📡 Streaming... {duration - i} seconds remaining")

        logger.info("🛑 Stopping video stream...")
        await producer.stop_streaming()

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        logger.info("🧹 Cleaning up...")
        if "producer" in locals():
            await producer.disconnect()
        logger.info("✅ Video producer example completed")


async def camera_example():
    """Example using actual camera (if available)"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("📷 Starting Camera Video Producer Example")

    try:
        # Create producer using factory function
        producer = await create_producer_client(base_url="http://localhost:8000")

        room_id = producer.current_room_id
        logger.info(f"🏠 Connected to room: {room_id}")

        # Get available cameras
        cameras = await producer.get_camera_devices()
        if cameras:
            logger.info("📹 Available cameras:")
            for camera in cameras:
                logger.info(
                    f"  Device {camera['device_id']}: {camera['name']} "
                    f"({camera['resolution']['width']}x{camera['resolution']['height']})"
                )

            # Start camera stream
            logger.info("📷 Starting camera stream...")
            await producer.start_camera(device_id=0)

            logger.info("📺 Camera streaming started!")
            logger.info(f"🔗 Consumers can connect to room: {room_id}")

            # Stream for demo duration
            await asyncio.sleep(30)

        else:
            logger.warning("⚠️  No cameras found")

    except Exception as e:
        logger.error(f"❌ Camera error: {e}")
        logger.info("💡 Make sure your camera is available and not used by other apps")
    finally:
        if "producer" in locals():
            await producer.disconnect()


async def screen_share_example():
    """Example using screen sharing (animated pattern for demo)"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("🖥️  Starting Screen Share Example")

    try:
        producer = await create_producer_client()
        room_id = producer.current_room_id

        logger.info("🖥️  Starting screen share...")
        await producer.start_screen_share()

        logger.info(f"📺 Screen sharing started! Room: {room_id}")

        # Share for demo duration
        await asyncio.sleep(20)

    except Exception as e:
        logger.error(f"❌ Screen share error: {e}")
    finally:
        if "producer" in locals():
            await producer.disconnect()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "camera":
            asyncio.run(camera_example())
        elif mode == "screen":
            asyncio.run(screen_share_example())
        elif mode == "animated":
            asyncio.run(main())
        else:
            print("Usage:")
            print("  python video_producer_example.py animated   # Animated content")
            print("  python video_producer_example.py camera     # Camera stream")
            print("  python video_producer_example.py screen     # Screen share")
    else:
        # Default: run animated example
        asyncio.run(main())
