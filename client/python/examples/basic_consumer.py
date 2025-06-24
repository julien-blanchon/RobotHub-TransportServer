#!/usr/bin/env python3
"""
Basic Consumer Example - RobotHub TransportServer

This example demonstrates:
- Connecting to an existing room as a consumer
- Receiving joint updates and state sync
- Setting up callbacks
- Getting current state
"""

import asyncio
import logging

from transport_server_client import RoboticsConsumer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Basic consumer example."""
    # You need to provide an existing workspace and room ID
    # You can get these from running basic_producer.py first
    print(
        "Enter connection details (you can get these from running basic_producer.py):"
    )
    workspace_id = input("Enter workspace ID: ").strip()
    room_id = input("Enter room ID: ").strip()

    if not workspace_id or not room_id:
        logger.error("Both workspace ID and room ID are required!")
        return

    # Create consumer client
    consumer = RoboticsConsumer("http://localhost:8000")

    # Track received updates
    received_updates = []
    received_states = []

    # Set up callbacks
    def on_joint_update(joints):
        logger.info(f"Received joint update: {joints}")
        received_updates.append(joints)

    def on_state_sync(state):
        logger.info(f"Received state sync: {state}")
        received_states.append(state)

    def on_error(error_msg):
        logger.error(f"Consumer error: {error_msg}")

    def on_connected():
        logger.info("Consumer connected!")

    def on_disconnected():
        logger.info("Consumer disconnected!")

    # Register all callbacks
    consumer.on_joint_update(on_joint_update)
    consumer.on_state_sync(on_state_sync)
    consumer.on_error(on_error)
    consumer.on_connected(on_connected)
    consumer.on_disconnected(on_disconnected)

    try:
        # Connect to the room
        success = await consumer.connect(workspace_id, room_id)
        if not success:
            logger.error("Failed to connect to room!")
            return

        logger.info(f"Connected to room {room_id} in workspace {workspace_id}")

        # Get initial state
        initial_state = await consumer.get_state_sync()
        logger.info(f"Initial state: {initial_state}")

        # Listen for updates for 30 seconds
        logger.info("Listening for updates for 30 seconds...")
        await asyncio.sleep(30)

        # Show summary
        logger.info(f"Received {len(received_updates)} joint updates")
        logger.info(f"Received {len(received_states)} state syncs")

    except Exception:
        logger.exception("Exception: ")
    finally:
        # Always disconnect
        if consumer.is_connected():
            await consumer.disconnect()
            logger.info("Consumer disconnected")


if __name__ == "__main__":
    asyncio.run(main())
