#!/usr/bin/env python3
"""
Basic Producer Example - LeRobot Arena

This example demonstrates:
- Creating a room
- Connecting as a producer
- Sending joint updates
- Basic error handling
"""

import asyncio
import logging

from lerobot_arena_client import RoboticsProducer

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

    producer.on_error(on_error)

    try:
        # Create a room and connect
        room_id = await producer.create_room()
        logger.info(f"Created room: {room_id}")

        # Connect as producer
        success = await producer.connect(room_id)
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

        # Keep alive for a bit
        await asyncio.sleep(2)

        logger.info("Example completed successfully!")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always disconnect
        if producer.is_connected():
            await producer.disconnect()
            logger.info("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
