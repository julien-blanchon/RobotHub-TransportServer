import asyncio

import pytest
from lerobot_arena_client import RoboticsProducer


class TestRoboticsProducer:
    """Test RoboticsProducer functionality."""

    @pytest.mark.asyncio
    async def test_producer_connection(self, producer, test_room):
        """Test basic producer connection."""
        assert not producer.is_connected()

        success = await producer.connect(test_room)
        assert success is True
        assert producer.is_connected()
        assert producer.room_id == test_room
        assert producer.role == "producer"

        await producer.disconnect()
        assert not producer.is_connected()

    @pytest.mark.asyncio
    async def test_producer_connection_info(self, connected_producer):
        """Test getting connection information."""
        producer, room_id = connected_producer

        info = producer.get_connection_info()
        assert info["connected"] is True
        assert info["room_id"] == room_id
        assert info["role"] == "producer"
        assert info["participant_id"] is not None
        assert info["base_url"] == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_send_joint_update(self, connected_producer):
        """Test sending joint updates."""
        producer, room_id = connected_producer

        joints = [
            {"name": "shoulder", "value": 45.0},
            {"name": "elbow", "value": -20.0},
            {"name": "wrist", "value": 10.0},
        ]

        # Should not raise an exception
        await producer.send_joint_update(joints)

    @pytest.mark.asyncio
    async def test_send_state_sync(self, connected_producer):
        """Test sending state synchronization."""
        producer, room_id = connected_producer

        state = {"shoulder": 45.0, "elbow": -20.0, "wrist": 10.0}

        # Should not raise an exception
        await producer.send_state_sync(state)

    @pytest.mark.asyncio
    async def test_send_emergency_stop(self, connected_producer):
        """Test sending emergency stop."""
        producer, room_id = connected_producer

        # Should not raise an exception
        await producer.send_emergency_stop("Test emergency stop")
        await producer.send_emergency_stop()  # Default reason

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, connected_producer):
        """Test sending heartbeat."""
        producer, room_id = connected_producer

        # Should not raise an exception
        await producer.send_heartbeat()

    @pytest.mark.asyncio
    async def test_producer_callbacks(self, producer, test_room):
        """Test producer event callbacks."""
        connected_called = False
        disconnected_called = False
        error_called = False
        error_message = None

        def on_connected():
            nonlocal connected_called
            connected_called = True

        def on_disconnected():
            nonlocal disconnected_called
            disconnected_called = True

        def on_error(error):
            nonlocal error_called, error_message
            error_called = True
            error_message = error

        # Set callbacks
        producer.on_connected(on_connected)
        producer.on_disconnected(on_disconnected)
        producer.on_error(on_error)

        # Connect and disconnect
        await producer.connect(test_room)
        await asyncio.sleep(0.1)  # Give callbacks time to execute
        assert connected_called is True

        await producer.disconnect()
        await asyncio.sleep(0.1)  # Give callbacks time to execute
        assert disconnected_called is True

    @pytest.mark.asyncio
    async def test_send_without_connection(self, producer):
        """Test that sending commands without connection raises errors."""
        assert not producer.is_connected()

        with pytest.raises(ValueError, match="Must be connected"):
            await producer.send_joint_update([{"name": "test", "value": 0}])

        with pytest.raises(ValueError, match="Must be connected"):
            await producer.send_state_sync({"test": 0})

        with pytest.raises(ValueError, match="Must be connected"):
            await producer.send_emergency_stop()

    @pytest.mark.asyncio
    async def test_multiple_connections(self, producer, test_room):
        """Test connecting to multiple rooms sequentially."""
        # Connect to first room
        await producer.connect(test_room)
        assert producer.room_id == test_room

        # Create second room
        room_id_2 = await producer.create_room()

        try:
            # Connect to second room (should disconnect from first)
            await producer.connect(room_id_2)
            assert producer.room_id == room_id_2
            assert producer.is_connected()

        finally:
            await producer.delete_room(room_id_2)

    @pytest.mark.asyncio
    async def test_context_manager(self, test_room):
        """Test using producer as context manager."""
        async with RoboticsProducer("http://localhost:8000") as producer:
            await producer.connect(test_room)
            assert producer.is_connected()

            await producer.send_state_sync({"test": 123.0})

        # Should be disconnected after context exit
        assert not producer.is_connected()

    @pytest.mark.asyncio
    async def test_duplicate_producer_connection(self, producer, test_room):
        """Test what happens when multiple producers try to connect to same room."""
        producer2 = RoboticsProducer("http://localhost:8000")

        try:
            # First producer connects successfully
            success1 = await producer.connect(test_room)
            assert success1 is True

            # Second producer should fail to connect as producer
            success2 = await producer2.connect(test_room)
            assert success2 is False  # Should fail since room already has producer

        finally:
            if producer2.is_connected():
                await producer2.disconnect()

    @pytest.mark.asyncio
    async def test_custom_participant_id(self, producer, test_room):
        """Test connecting with custom participant ID."""
        custom_id = "custom-producer-123"

        await producer.connect(test_room, participant_id=custom_id)

        info = producer.get_connection_info()
        assert info["participant_id"] == custom_id

    @pytest.mark.asyncio
    async def test_large_joint_update(self, connected_producer):
        """Test sending large joint update."""
        producer, room_id = connected_producer

        # Create a large joint update
        joints = []
        for i in range(100):
            joints.append({"name": f"joint_{i}", "value": float(i)})

        # Should handle large updates without issue
        await producer.send_joint_update(joints)

    @pytest.mark.asyncio
    async def test_rapid_updates(self, connected_producer):
        """Test sending rapid joint updates."""
        producer, room_id = connected_producer

        # Send multiple rapid updates
        for i in range(10):
            await producer.send_state_sync({"joint1": float(i), "joint2": float(i * 2)})
            await asyncio.sleep(0.01)  # Small delay
