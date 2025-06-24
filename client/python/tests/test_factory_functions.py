import asyncio

import pytest
from lerobot_arena_client import (
    RoboticsConsumer,
    RoboticsProducer,
    create_client,
    create_consumer_client,
    create_producer_client,
)


class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_create_client_producer(self):
        """Test creating producer client via factory."""
        client = create_client("producer", "http://localhost:8000")
        assert isinstance(client, RoboticsProducer)
        assert client.base_url == "http://localhost:8000"
        assert not client.is_connected()

    def test_create_client_consumer(self):
        """Test creating consumer client via factory."""
        client = create_client("consumer", "http://localhost:8000")
        assert isinstance(client, RoboticsConsumer)
        assert client.base_url == "http://localhost:8000"
        assert not client.is_connected()

    def test_create_client_invalid_role(self):
        """Test creating client with invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            create_client("invalid_role", "http://localhost:8000")

    def test_create_client_default_url(self):
        """Test creating client with default URL."""
        producer = create_client("producer")
        consumer = create_client("consumer")

        assert producer.base_url == "http://localhost:8000"
        assert consumer.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_create_producer_client_auto_room(self):
        """Test creating producer client with auto room creation."""
        producer = await create_producer_client("http://localhost:8000")

        try:
            assert isinstance(producer, RoboticsProducer)
            assert producer.is_connected()
            assert producer.room_id is not None
            assert producer.role == "producer"

            # Should be able to send commands immediately
            await producer.send_state_sync({"test": 123.0})

        finally:
            room_id = producer.room_id
            await producer.disconnect()
            if room_id:
                await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_create_producer_client_specific_room(self):
        """Test creating producer client with specific room."""
        # First create a room
        temp_producer = RoboticsProducer("http://localhost:8000")
        room_id = await temp_producer.create_room()

        try:
            producer = await create_producer_client("http://localhost:8000", room_id)

            assert isinstance(producer, RoboticsProducer)
            assert producer.is_connected()
            assert producer.room_id == room_id
            assert producer.role == "producer"

            await producer.disconnect()

        finally:
            await temp_producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_create_consumer_client(self):
        """Test creating consumer client."""
        # First create a room
        temp_producer = RoboticsProducer("http://localhost:8000")
        room_id = await temp_producer.create_room()

        try:
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            assert isinstance(consumer, RoboticsConsumer)
            assert consumer.is_connected()
            assert consumer.room_id == room_id
            assert consumer.role == "consumer"

            # Should be able to get state immediately
            state = await consumer.get_state_sync()
            assert isinstance(state, dict)

            await consumer.disconnect()

        finally:
            await temp_producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_create_producer_consumer_pair(self):
        """Test creating producer-consumer pair using convenience functions."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            # Both should be connected to same room
            assert producer.room_id == consumer.room_id
            assert producer.is_connected()
            assert consumer.is_connected()

            # Test communication
            received_updates = []

            def on_joint_update(joints):
                received_updates.append(joints)

            consumer.on_joint_update(on_joint_update)

            # Give some time for connection to stabilize
            await asyncio.sleep(0.1)

            # Send update from producer
            await producer.send_state_sync({"test_joint": 42.0})

            # Wait for message
            await asyncio.sleep(0.2)

            # Consumer should have received update
            assert len(received_updates) >= 1

            await consumer.disconnect()

        finally:
            await producer.disconnect()
            if room_id:
                await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_convenience_functions_with_default_url(self):
        """Test convenience functions with default URL."""
        producer = await create_producer_client()
        room_id = producer.room_id

        try:
            assert producer.base_url == "http://localhost:8000"
            assert producer.is_connected()

            consumer = await create_consumer_client(room_id)

            try:
                assert consumer.base_url == "http://localhost:8000"
                assert consumer.is_connected()

            finally:
                await consumer.disconnect()

        finally:
            await producer.disconnect()
            if room_id:
                await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_multiple_convenience_producers(self):
        """Test creating multiple producers via convenience function."""
        producer1 = await create_producer_client("http://localhost:8000")
        producer2 = await create_producer_client("http://localhost:8000")

        try:
            # Both should be connected to different rooms
            assert producer1.room_id != producer2.room_id
            assert producer1.is_connected()
            assert producer2.is_connected()

            # Both should work independently
            await producer1.send_state_sync({"joint1": 10.0})
            await producer2.send_state_sync({"joint2": 20.0})

        finally:
            room1 = producer1.room_id
            room2 = producer2.room_id

            await producer1.disconnect()
            await producer2.disconnect()

            if room1:
                await producer1.delete_room(room1)
            if room2:
                await producer2.delete_room(room2)

    @pytest.mark.asyncio
    async def test_create_consumer_nonexistent_room(self):
        """Test creating consumer with nonexistent room."""
        fake_room_id = "nonexistent-room-12345"

        try:
            consumer = await create_consumer_client(
                fake_room_id, "http://localhost:8000"
            )
            # If this succeeds, the server creates room automatically
            # or connection fails silently
            if consumer.is_connected():
                await consumer.disconnect()
        except Exception:
            # Expected behavior - connection should fail
            pass
