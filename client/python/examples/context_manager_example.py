#!/usr/bin/env python3
"""
Context Manager Example - RobotHub TransportServer

This example demonstrates:
- Using clients as context managers for automatic cleanup
- Exception handling with proper resource cleanup
- Factory functions for quick client creation
- Graceful error recovery
"""

import asyncio
import logging

from transport_server_client import (
    RoboticsConsumer,
    RoboticsProducer,
    create_consumer_client,
    create_producer_client,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_context_manager_example():
    """Basic example using context managers."""
    logger.info("=== Basic Context Manager Example ===")

    # Using producer as context manager
    async with RoboticsProducer("http://localhost:8000") as producer:
        workspace_id, room_id = await producer.create_room()
        logger.info(f"Created room: {room_id}")
        logger.info(f"Workspace ID: {workspace_id}")

        await producer.connect(workspace_id, room_id)
        logger.info("Producer connected")

        # Send some data
        await producer.send_state_sync({"joint1": 45.0, "joint2": -30.0})
        logger.info("State sent")

        # Exception handling within context
        try:
            # This might fail if room doesn't exist
            await producer.send_joint_update([{"name": "invalid", "value": 999.0}])
        except Exception:
            logger.exception("Handled exception")

        # Clean up room before context exit
        await producer.delete_room(workspace_id, room_id)

    # Producer is automatically disconnected here
    logger.info("Producer automatically disconnected")


async def factory_function_example():
    """Example using factory functions for quick setup."""
    logger.info("\n=== Factory Function Example ===")

    # Create and auto-connect producer with factory function
    producer = await create_producer_client("http://localhost:8000")
    workspace_id = producer.workspace_id
    room_id = producer.room_id
    logger.info(f"Producer auto-connected to room: {room_id}")
    logger.info(f"Workspace ID: {workspace_id}")

    try:
        # Create and auto-connect consumer
        consumer = await create_consumer_client(
            workspace_id, room_id, "http://localhost:8000"
        )
        logger.info("Consumer auto-connected")

        # Set up callback
        received_updates = []
        consumer.on_joint_update(received_updates.append)

        # Send some updates
        await producer.send_joint_update([
            {"name": "shoulder", "value": 90.0},
            {"name": "elbow", "value": -45.0},
        ])

        await asyncio.sleep(0.5)  # Wait for message propagation

        logger.info(f"Consumer received {len(received_updates)} updates")

    finally:
        # Manual cleanup for factory-created clients
        await consumer.disconnect()
        await producer.disconnect()
        await producer.delete_room(workspace_id, room_id)
        logger.info("Manual cleanup completed")


async def exception_handling_example():
    """Example showing exception handling with context managers."""
    logger.info("\n=== Exception Handling Example ===")

    workspace_id = None
    room_id = None

    try:
        async with RoboticsProducer("http://localhost:8000") as producer:
            workspace_id, room_id = await producer.create_room()
            await producer.connect(workspace_id, room_id)

            # Simulate some work that might fail
            for i in range(5):
                if i == 3:
                    # Simulate an error
                    msg = "Simulated error during operation"
                    raise ValueError(msg)

                await producer.send_state_sync({f"joint_{i}": float(i * 10)})
                logger.info(f"Sent update {i}")
                await asyncio.sleep(0.1)

    except ValueError:
        logger.exception("Caught expected error")
        logger.info("Context manager still ensures cleanup")

    # Clean up room after exception
    if workspace_id and room_id:
        try:
            temp_producer = RoboticsProducer("http://localhost:8000")
            await temp_producer.delete_room(workspace_id, room_id)
            logger.info("Room cleaned up after exception")
        except Exception:
            logger.exception("Failed to clean up room")

    logger.info("Exception handling example completed")


async def multiple_clients_example():
    """Example with multiple clients using context managers."""
    logger.info("\n=== Multiple Clients Example ===")

    # Create room first
    workspace_id = None
    room_id = None
    async with RoboticsProducer("http://localhost:8000") as setup_producer:
        workspace_id, room_id = await setup_producer.create_room()
        logger.info(f"Setup room: {room_id}")
        logger.info(f"Workspace ID: {workspace_id}")

    # Now use multiple clients in the same room
    async with RoboticsProducer("http://localhost:8000") as producer:
        await producer.connect(workspace_id, room_id)

        # Use multiple consumers
        consumers = []
        try:
            # Create multiple consumers with context managers
            for i in range(3):
                consumer = RoboticsConsumer("http://localhost:8000")
                consumers.append(consumer)
                # Note: We're not using context manager here to show manual management
                await consumer.connect(workspace_id, room_id, f"consumer-{i}")

            logger.info(f"Connected {len(consumers)} consumers")

            # Send data to all consumers
            await producer.send_state_sync({
                "base": 0.0,
                "shoulder": 45.0,
                "elbow": -30.0,
                "wrist": 15.0,
            })

            await asyncio.sleep(0.5)  # Wait for propagation
            logger.info("Data sent to all consumers")

        finally:
            # Manual cleanup for consumers
            for i, consumer in enumerate(consumers):
                await consumer.disconnect()
                logger.info(f"Disconnected consumer-{i}")

    # Clean up room
    if workspace_id and room_id:
        try:
            temp_producer = RoboticsProducer("http://localhost:8000")
            await temp_producer.delete_room(workspace_id, room_id)
            logger.info("Room cleaned up")
        except Exception:
            logger.exception("Failed to clean up room")

    logger.info("Multiple clients example completed")


async def main():
    """Run all context manager examples."""
    logger.info("🤖 RobotHub TransportServer Context Manager Examples 🤖")

    try:
        await basic_context_manager_example()
        await factory_function_example()
        await exception_handling_example()
        await multiple_clients_example()

        logger.info("\n✅ All context manager examples completed successfully!")

    except Exception:
        logger.exception("❌ Example failed")


if __name__ == "__main__":
    asyncio.run(main())
