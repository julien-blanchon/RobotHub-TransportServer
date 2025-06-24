import asyncio

import pytest
from lerobot_arena_client import (
    RoboticsProducer,
    create_consumer_client,
    create_producer_client,
)


class TestIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_producer_consumer_workflow(self):
        """Test complete producer-consumer workflow."""
        # Create producer and room
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            # Create consumer and connect to same room
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                # Set up consumer to collect messages
                received_states = []
                received_updates = []
                received_errors = []

                def on_state_sync(state):
                    received_states.append(state)

                def on_joint_update(joints):
                    received_updates.append(joints)

                def on_error(error):
                    received_errors.append(error)

                consumer.on_state_sync(on_state_sync)
                consumer.on_joint_update(on_joint_update)
                consumer.on_error(on_error)

                # Wait for connections to stabilize
                await asyncio.sleep(0.2)

                # Producer sends initial state
                initial_state = {"shoulder": 0.0, "elbow": 0.0, "wrist": 0.0}
                await producer.send_state_sync(initial_state)
                await asyncio.sleep(0.1)

                # Producer sends series of joint updates
                joint_sequences = [
                    [{"name": "shoulder", "value": 45.0}],
                    [{"name": "elbow", "value": -30.0}],
                    [{"name": "wrist", "value": 15.0}],
                    [
                        {"name": "shoulder", "value": 90.0},
                        {"name": "elbow", "value": -60.0},
                    ],
                ]

                for joints in joint_sequences:
                    await producer.send_joint_update(joints)
                    await asyncio.sleep(0.1)

                # Wait for all messages to be received
                await asyncio.sleep(0.3)

                # Verify consumer received messages
                assert len(received_updates) >= 4  # At least the joint updates

                # Verify final state
                final_state = await consumer.get_state_sync()
                expected_final_state = {"shoulder": 90.0, "elbow": -60.0, "wrist": 15.0}
                assert final_state == expected_final_state

            finally:
                await consumer.disconnect()

        finally:
            await producer.disconnect()
            await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_multiple_consumers_same_room(self):
        """Test multiple consumers receiving same messages."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            # Create multiple consumers
            consumer1 = await create_consumer_client(room_id, "http://localhost:8000")
            consumer2 = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                # Set up message collection for both consumers
                consumer1_updates = []
                consumer2_updates = []

                consumer1.on_joint_update(
                    lambda joints: consumer1_updates.append(joints)
                )
                consumer2.on_joint_update(
                    lambda joints: consumer2_updates.append(joints)
                )

                # Wait for connections
                await asyncio.sleep(0.2)

                # Producer sends updates
                test_joints = [
                    {"name": "joint1", "value": 10.0},
                    {"name": "joint2", "value": 20.0},
                ]
                await producer.send_joint_update(test_joints)

                # Wait for message propagation
                await asyncio.sleep(0.2)

                # Both consumers should receive the same update
                assert len(consumer1_updates) >= 1
                assert len(consumer2_updates) >= 1

                # Verify both received same data
                if consumer1_updates and consumer2_updates:
                    assert consumer1_updates[-1] == consumer2_updates[-1]

            finally:
                await consumer1.disconnect()
                await consumer2.disconnect()

        finally:
            await producer.disconnect()
            await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_emergency_stop_propagation(self):
        """Test emergency stop propagation to all consumers."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            # Create consumers
            consumer1 = await create_consumer_client(room_id, "http://localhost:8000")
            consumer2 = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                # Set up error collection
                consumer1_errors = []
                consumer2_errors = []

                consumer1.on_error(lambda error: consumer1_errors.append(error))
                consumer2.on_error(lambda error: consumer2_errors.append(error))

                # Wait for connections
                await asyncio.sleep(0.2)

                # Producer sends emergency stop
                await producer.send_emergency_stop("Integration test emergency stop")

                # Wait for message propagation
                await asyncio.sleep(0.2)

                # Both consumers should receive emergency stop
                assert len(consumer1_errors) >= 1
                assert len(consumer2_errors) >= 1

                # Verify error messages contain emergency stop info
                if consumer1_errors:
                    assert "emergency stop" in consumer1_errors[-1].lower()
                if consumer2_errors:
                    assert "emergency stop" in consumer2_errors[-1].lower()

            finally:
                await consumer1.disconnect()
                await consumer2.disconnect()

        finally:
            await producer.disconnect()
            await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_producer_reconnection_workflow(self):
        """Test producer reconnecting and resuming operation."""
        # Create room first
        temp_producer = RoboticsProducer("http://localhost:8000")
        room_id = await temp_producer.create_room()

        try:
            # Create consumer first
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                received_updates = []
                consumer.on_joint_update(lambda joints: received_updates.append(joints))

                # Create producer and connect
                producer = RoboticsProducer("http://localhost:8000")
                await producer.connect(room_id)

                # Send initial update
                await producer.send_state_sync({"joint1": 10.0})
                await asyncio.sleep(0.1)

                # Disconnect producer
                await producer.disconnect()

                # Reconnect producer
                await producer.connect(room_id)

                # Send another update
                await producer.send_state_sync({"joint1": 20.0})
                await asyncio.sleep(0.2)

                # Consumer should have received both updates
                assert len(received_updates) >= 2

                await producer.disconnect()

            finally:
                await consumer.disconnect()

        finally:
            await temp_producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_consumer_late_join(self):
        """Test consumer joining room after producer has sent updates."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            # Producer sends some updates before consumer joins
            await producer.send_state_sync({"joint1": 10.0, "joint2": 20.0})
            await asyncio.sleep(0.1)

            await producer.send_joint_update([{"name": "joint3", "value": 30.0}])
            await asyncio.sleep(0.1)

            # Now consumer joins
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                # Consumer should be able to get current state
                current_state = await consumer.get_state_sync()

                # Should contain all previously sent updates
                expected_state = {"joint1": 10.0, "joint2": 20.0, "joint3": 30.0}
                assert current_state == expected_state

            finally:
                await consumer.disconnect()

        finally:
            await producer.disconnect()
            await producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_room_cleanup_on_producer_disconnect(self):
        """Test room state when producer disconnects."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                # Send some state
                await producer.send_state_sync({"joint1": 42.0})
                await asyncio.sleep(0.1)

                # Verify state exists
                state_before = await consumer.get_state_sync()
                assert state_before == {"joint1": 42.0}

                # Producer disconnects
                await producer.disconnect()
                await asyncio.sleep(0.1)

                # State should still be accessible to consumer
                state_after = await consumer.get_state_sync()
                assert state_after == {"joint1": 42.0}

            finally:
                await consumer.disconnect()

        finally:
            # Clean up room manually since producer disconnected
            temp_producer = RoboticsProducer("http://localhost:8000")
            await temp_producer.delete_room(room_id)

    @pytest.mark.asyncio
    async def test_high_frequency_updates(self):
        """Test handling high frequency updates."""
        producer = await create_producer_client("http://localhost:8000")
        room_id = producer.room_id

        try:
            consumer = await create_consumer_client(room_id, "http://localhost:8000")

            try:
                received_updates = []
                consumer.on_joint_update(lambda joints: received_updates.append(joints))

                # Wait for connection
                await asyncio.sleep(0.1)

                # Send rapid updates
                for i in range(20):
                    await producer.send_state_sync({"joint1": float(i), "timestamp": i})
                    await asyncio.sleep(0.01)  # 10ms intervals

                # Wait for all messages
                await asyncio.sleep(0.5)

                # Should have received multiple updates
                # (exact number may vary due to change detection)
                assert len(received_updates) >= 5

                # Final state should reflect last update
                final_state = await consumer.get_state_sync()
                assert final_state["joint1"] == 19.0
                assert final_state["timestamp"] == 19

            finally:
                await consumer.disconnect()

        finally:
            await producer.disconnect()
            await producer.delete_room(room_id)
