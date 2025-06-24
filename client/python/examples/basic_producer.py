#!/usr/bin/env python3
"""
Basic Producer Example - RobotHub TransportServer

This example demonstrates:
- Creating a room with workspace
- Connecting as a producer
- Sending joint updates
- Basic error handling
"""

import asyncio
import logging

from transport_server_client import RoboticsProducer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Basic producer example."""
    # Create producer client
    producer = RoboticsProducer("http://localhost:8000")

    # Set up error callback
    def on_error(error_msg):
        logger.error(f"Producer error: {error_msg}")

    def on_connected():
        logger.info("Producer connected!")

    def on_disconnected():
        logger.info("Producer disconnected!")

    producer.on_error(on_error)
    producer.on_connected(on_connected)
    producer.on_disconnected(on_disconnected)

    try:
        # Create a room and connect
        workspace_id, room_id = await producer.create_room()
        logger.info(f"Created room: {room_id}")
        logger.info(f"Workspace ID: {workspace_id}")

        # Connect as producer
        success = await producer.connect(workspace_id, room_id)
        if not success:
            logger.error("Failed to connect!")
            return

        logger.info("Connected as producer!")

        # Send some joint updates
        joints = [
            {"name": "shoulder", "value": 45.0},
            {"name": "elbow", "value": -20.0},
            {"name": "wrist", "value": 10.0},
        ]

        logger.info("Sending joint updates...")
        await producer.send_joint_update(joints)

        # Send state sync (converted to joint updates)
        state = {"shoulder": 90.0, "elbow": -45.0, "wrist": 0.0}

        logger.info("Sending state sync...")
        await producer.send_state_sync(state)

        # Send a heartbeat
        await producer.send_heartbeat()

        # Keep alive for a bit
        await asyncio.sleep(2)

        logger.info("Example completed successfully!")

    except Exception:
        logger.exception("Error")
    finally:
        # Always disconnect and cleanup
        if producer.is_connected():
            await producer.disconnect()
            logger.info("Disconnected")

        # Clean up the room we created
        if "workspace_id" in locals() and "room_id" in locals():
            try:
                await producer.delete_room(workspace_id, room_id)
                logger.info("Room cleaned up")
            except Exception:
                logger.exception("Failed to clean up room")


if __name__ == "__main__":
    asyncio.run(main())
