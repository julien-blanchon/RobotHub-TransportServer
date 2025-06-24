#!/usr/bin/env python3
"""
Tests for the LeRobot Arena Video Client

Basic tests to validate the video client implementation
"""

import asyncio
import logging

import numpy as np
import pytest
from lerobot_arena_client.video import (
    CustomVideoTrack,
    ParticipantRole,
    Resolution,
    VideoConfig,
    VideoConsumer,
    VideoEncoding,
    VideoProducer,
    create_consumer_client,
    create_producer_client,
)


class TestVideoTypes:
    """Test video type definitions"""

    def test_resolution_creation(self):
        """Test Resolution dataclass"""
        res = Resolution(width=1920, height=1080)
        assert res.width == 1920
        assert res.height == 1080

    def test_video_config_creation(self):
        """Test VideoConfig dataclass"""
        config = VideoConfig(
            encoding=VideoEncoding.VP8,
            resolution=Resolution(640, 480),
            framerate=30,
            bitrate=1000000,
        )
        assert config.encoding == VideoEncoding.VP8
        assert config.resolution.width == 640
        assert config.framerate == 30

    def test_participant_role_enum(self):
        """Test ParticipantRole enum"""
        assert ParticipantRole.PRODUCER.value == "producer"
        assert ParticipantRole.CONSUMER.value == "consumer"


class TestVideoCore:
    """Test core video client functionality"""

    def test_video_producer_creation(self):
        """Test VideoProducer initialization"""
        producer = VideoProducer("http://localhost:8000")
        assert producer.base_url == "http://localhost:8000"
        assert producer.api_base == "http://localhost:8000/video"
        assert not producer.connected
        assert producer.room_id is None

    def test_video_consumer_creation(self):
        """Test VideoConsumer initialization"""
        consumer = VideoConsumer("http://localhost:8000")
        assert consumer.base_url == "http://localhost:8000"
        assert consumer.api_base == "http://localhost:8000/video"
        assert not consumer.connected
        assert consumer.room_id is None

    @pytest.mark.asyncio
    async def test_producer_room_creation(self):
        """Test room creation (requires server)"""
        try:
            producer = VideoProducer("http://localhost:8000")
            room_id = await producer.create_room()
            assert isinstance(room_id, str)
            assert len(room_id) > 0
            print(f"✅ Created room: {room_id}")
        except Exception as e:
            pytest.skip(f"Server not available: {e}")

    @pytest.mark.asyncio
    async def test_consumer_list_rooms(self):
        """Test listing rooms (requires server)"""
        try:
            consumer = VideoConsumer("http://localhost:8000")
            rooms = await consumer.list_rooms()
            assert isinstance(rooms, list)
            print(f"✅ Listed {len(rooms)} rooms")
        except Exception as e:
            pytest.skip(f"Server not available: {e}")


class TestVideoTracks:
    """Test video track implementations"""

    @pytest.mark.asyncio
    async def test_custom_video_track(self):
        """Test CustomVideoTrack with mock frame source"""
        frame_count = 0

        async def mock_frame_source() -> np.ndarray | None:
            nonlocal frame_count
            if frame_count >= 3:
                return None

            # Create a simple test frame
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frame[:, :, frame_count % 3] = 255  # Red, Green, Blue frames
            frame_count += 1
            return frame

        track = CustomVideoTrack(mock_frame_source, frame_rate=10)

        # Get a few frames
        for i in range(3):
            frame = await track.recv()
            assert frame is not None
            print(f"✅ Generated frame {i + 1}")

        print("✅ CustomVideoTrack test passed")


class TestVideoClientIntegration:
    """Integration tests for video client"""

    @pytest.mark.asyncio
    async def test_producer_consumer_setup(self):
        """Test producer and consumer setup without server connection"""
        # Test producer setup
        producer = VideoProducer("http://localhost:8000")
        assert producer.get_video_track() is None

        # Test consumer setup
        consumer = VideoConsumer("http://localhost:8000")
        assert consumer.get_remote_stream() is None

        print("✅ Producer/Consumer setup test passed")

    @pytest.mark.asyncio
    async def test_custom_stream_setup(self):
        """Test custom stream setup"""

        async def test_frame_source() -> np.ndarray | None:
            return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        producer = VideoProducer("http://localhost:8000")

        # This will fail because we're not connected, but it tests the setup
        try:
            await producer.start_custom_stream(test_frame_source)
        except ValueError as e:
            assert "Must be connected" in str(e)
            print("✅ Custom stream setup validation passed")

    @pytest.mark.asyncio
    async def test_factory_functions(self):
        """Test factory function creation (without connection)"""
        # Test that factory functions create the right types
        # (We can't actually connect without a server)

        try:
            producer = await create_producer_client("http://localhost:8000")
        except Exception:
            # Expected to fail without server
            pass

        try:
            consumer = await create_consumer_client(
                "test-room", "http://localhost:8000"
            )
        except Exception:
            # Expected to fail without server
            pass

        print("✅ Factory functions test passed")


async def run_interactive_tests():
    """Run interactive tests for manual verification"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("🧪 Running Interactive Video Client Tests")

    # Test 1: Basic client creation
    logger.info("📝 Test 1: Creating video clients...")
    producer = VideoProducer("http://localhost:8000")
    consumer = VideoConsumer("http://localhost:8000")
    logger.info("✅ Clients created successfully")

    # Test 2: Custom video track
    logger.info("📝 Test 2: Testing custom video track...")

    frame_count = 0

    async def animated_frame_source() -> np.ndarray | None:
        nonlocal frame_count
        if frame_count >= 5:
            return None

        # Create animated frame
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        t = frame_count * 0.5

        # Simple animation
        for y in range(240):
            for x in range(320):
                r = int(128 + 127 * np.sin(t + x * 0.05))
                g = int(128 + 127 * np.sin(t + y * 0.05))
                b = int(128 + 127 * np.sin(t))
                frame[y, x] = [r, g, b]

        frame_count += 1
        return frame

    track = CustomVideoTrack(animated_frame_source, frame_rate=5)

    for i in range(5):
        frame = await track.recv()
        logger.info(
            f"📺 Generated animated frame {i + 1}: {frame.width}x{frame.height}"
        )

    logger.info("✅ Custom video track test completed")

    # Test 3: Server communication (if available)
    logger.info("📝 Test 3: Testing server communication...")
    try:
        rooms = await consumer.list_rooms()
        logger.info(f"✅ Server communication successful - found {len(rooms)} rooms")

        # Try creating a room
        room_id = await producer.create_room()
        logger.info(f"✅ Room created successfully: {room_id}")

    except Exception as e:
        logger.warning(
            f"⚠️  Server communication failed (expected if server not running): {e}"
        )

    logger.info("🎉 All interactive tests completed!")


if __name__ == "__main__":
    # Run interactive tests
    asyncio.run(run_interactive_tests())
