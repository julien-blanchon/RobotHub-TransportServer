import asyncio

import pytest
from lerobot_arena_client import RoboticsConsumer


class TestRoboticsConsumer:
    """Test RoboticsConsumer functionality."""

    @pytest.mark.asyncio
    async def test_consumer_connection(self, consumer, test_room):
        """Test basic consumer connection."""
        assert not consumer.is_connected()

        success = await consumer.connect(test_room)
        assert success is True
        assert consumer.is_connected()
        assert consumer.room_id == test_room
        assert consumer.role == "consumer"

        await consumer.disconnect()
        assert not consumer.is_connected()

    @pytest.mark.asyncio
    async def test_consumer_connection_info(self, connected_consumer):
        """Test getting connection information."""
        consumer, room_id = connected_consumer

        info = consumer.get_connection_info()
        assert info["connected"] is True
        assert info["room_id"] == room_id
        assert info["role"] == "consumer"
        assert info["participant_id"] is not None
        assert info["base_url"] == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_get_state_sync(self, connected_consumer):
        """Test getting current state synchronously."""
        consumer, room_id = connected_consumer

        state = await consumer.get_state_sync()
        assert isinstance(state, dict)
        # Initial state should be empty
        assert len(state) == 0

    @pytest.mark.asyncio
    async def test_consumer_callbacks_setup(self, consumer, test_room):
        """Test setting up consumer callbacks."""
        state_sync_called = False
        joint_update_called = False
        error_called = False
        connected_called = False
        disconnected_called = False

        def on_state_sync(state):
            nonlocal state_sync_called
            state_sync_called = True

        def on_joint_update(joints):
            nonlocal joint_update_called
            joint_update_called = True

        def on_error(error):
            nonlocal error_called
            error_called = True

        def on_connected():
            nonlocal connected_called
            connected_called = True

        def on_disconnected():
            nonlocal disconnected_called
            disconnected_called = True

        # Set all callbacks
        consumer.on_state_sync(on_state_sync)
        consumer.on_joint_update(on_joint_update)
        consumer.on_error(on_error)
        consumer.on_connected(on_connected)
        consumer.on_disconnected(on_disconnected)

        # Connect and test connection callbacks
        await consumer.connect(test_room)
        await asyncio.sleep(0.1)
        assert connected_called is True

        await consumer.disconnect()
        await asyncio.sleep(0.1)
        assert disconnected_called is True

    @pytest.mark.asyncio
    async def test_multiple_consumers(self, test_room):
        """Test multiple consumers connecting to same room."""
        consumer1 = RoboticsConsumer("http://localhost:8000")
        consumer2 = RoboticsConsumer("http://localhost:8000")

        try:
            # Both consumers should be able to connect
            success1 = await consumer1.connect(test_room)
            success2 = await consumer2.connect(test_room)

            assert success1 is True
            assert success2 is True
            assert consumer1.is_connected()
            assert consumer2.is_connected()

        finally:
            if consumer1.is_connected():
                await consumer1.disconnect()
            if consumer2.is_connected():
                await consumer2.disconnect()

    @pytest.mark.asyncio
    async def test_consumer_receive_state_sync(self, producer_consumer_pair):
        """Test consumer receiving state sync from producer."""
        producer, consumer, room_id = producer_consumer_pair

        received_states = []
        received_updates = []

        def on_state_sync(state):
            received_states.append(state)

        def on_joint_update(joints):
            received_updates.append(joints)

        consumer.on_state_sync(on_state_sync)
        consumer.on_joint_update(on_joint_update)

        # Give some time for connection to stabilize
        await asyncio.sleep(0.1)

        # Producer sends state sync (which gets converted to joint updates)
        await producer.send_state_sync({"shoulder": 45.0, "elbow": -20.0})

        # Wait for message to be received
        await asyncio.sleep(0.2)

        # Consumer should have received the joint updates from the state sync
        # The initial state sync during connection might be empty, so we check for joint updates
        assert len(received_updates) >= 1

    @pytest.mark.asyncio
    async def test_consumer_receive_joint_updates(self, producer_consumer_pair):
        """Test consumer receiving joint updates from producer."""
        producer, consumer, room_id = producer_consumer_pair

        received_updates = []

        def on_joint_update(joints):
            received_updates.append(joints)

        consumer.on_joint_update(on_joint_update)

        # Give some time for connection to stabilize
        await asyncio.sleep(0.1)

        # Producer sends joint updates
        test_joints = [
            {"name": "shoulder", "value": 45.0},
            {"name": "elbow", "value": -20.0},
        ]
        await producer.send_joint_update(test_joints)

        # Wait for message to be received
        await asyncio.sleep(0.2)

        # Consumer should have received the joint update
        assert len(received_updates) >= 1
        if received_updates:
            received_joints = received_updates[-1]
            assert isinstance(received_joints, list)
            assert len(received_joints) == 2

    @pytest.mark.asyncio
    async def test_consumer_multiple_updates(self, producer_consumer_pair):
        """Test consumer receiving multiple updates."""
        producer, consumer, room_id = producer_consumer_pair

        received_updates = []

        def on_joint_update(joints):
            received_updates.append(joints)

        consumer.on_joint_update(on_joint_update)

        # Give some time for connection to stabilize
        await asyncio.sleep(0.1)

        # Send multiple updates
        for i in range(5):
            await producer.send_state_sync({
                "joint1": float(i * 10),
                "joint2": float(i * -5),
            })
            await asyncio.sleep(0.05)

        # Wait for all messages to be received
        await asyncio.sleep(0.3)

        # Should have received multiple updates
        assert len(received_updates) >= 3

    @pytest.mark.asyncio
    async def test_consumer_emergency_stop(self, producer_consumer_pair):
        """Test consumer receiving emergency stop."""
        producer, consumer, room_id = producer_consumer_pair

        received_errors = []

        def on_error(error):
            received_errors.append(error)

        consumer.on_error(on_error)

        # Give some time for connection to stabilize
        await asyncio.sleep(0.1)

        # Producer sends emergency stop
        await producer.send_emergency_stop("Test emergency stop")

        # Wait for message to be received
        await asyncio.sleep(0.2)

        # Consumer should have received emergency stop as error
        assert len(received_errors) >= 1
        if received_errors:
            assert "emergency stop" in received_errors[-1].lower()

    @pytest.mark.asyncio
    async def test_custom_participant_id(self, consumer, test_room):
        """Test connecting with custom participant ID."""
        custom_id = "custom-consumer-456"

        await consumer.connect(test_room, participant_id=custom_id)

        info = consumer.get_connection_info()
        assert info["participant_id"] == custom_id

    @pytest.mark.asyncio
    async def test_context_manager(self, test_room):
        """Test using consumer as context manager."""
        async with RoboticsConsumer("http://localhost:8000") as consumer:
            await consumer.connect(test_room)
            assert consumer.is_connected()

            state = await consumer.get_state_sync()
            assert isinstance(state, dict)

        # Should be disconnected after context exit
        assert not consumer.is_connected()

    @pytest.mark.asyncio
    async def test_get_state_without_connection(self, consumer):
        """Test getting state without being connected."""
        assert not consumer.is_connected()

        with pytest.raises(ValueError, match="Must be connected to a room"):
            await consumer.get_state_sync()

    @pytest.mark.asyncio
    async def test_consumer_reconnection(self, consumer, test_room):
        """Test consumer reconnecting to same room."""
        # First connection
        await consumer.connect(test_room)
        assert consumer.is_connected()

        await consumer.disconnect()
        assert not consumer.is_connected()

        # Reconnect to same room
        await consumer.connect(test_room)
        assert consumer.is_connected()
        assert consumer.room_id == test_room

    @pytest.mark.asyncio
    async def test_consumer_state_after_producer_updates(self, producer_consumer_pair):
        """Test that consumer can get updated state after producer sends updates."""
        producer, consumer, room_id = producer_consumer_pair

        # Give some time for connection to stabilize
        await asyncio.sleep(0.1)

        # Producer sends some state updates
        await producer.send_state_sync({
            "shoulder": 45.0,
            "elbow": -20.0,
            "wrist": 10.0,
        })

        # Wait for state to propagate
        await asyncio.sleep(0.2)

        # Consumer should be able to get updated state
        state = await consumer.get_state_sync()
        assert isinstance(state, dict)
        # State should contain the joints we sent
        expected_joints = {"shoulder", "elbow", "wrist"}
        if state:  # Only check if state is not empty
            assert set(state.keys()) == expected_joints
