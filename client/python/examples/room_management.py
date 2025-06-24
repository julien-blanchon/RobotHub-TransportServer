#!/usr/bin/env python3
"""
Room Management Example - LeRobot Arena

This example demonstrates:
- Listing rooms
- Creating rooms (with and without custom IDs)
- Getting room information
- Getting room state
- Deleting rooms
"""

import asyncio
import logging

from lerobot_arena_client import RoboticsClientCore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Room management example."""
    # Create a basic client for API operations
    client = RoboticsClientCore("http://localhost:8000")

    try:
        # List existing rooms
        logger.info("=== Listing existing rooms ===")
        rooms = await client.list_rooms()
        logger.info(f"Found {len(rooms)} rooms:")
        for room in rooms:
            logger.info(
                f"  - {room['id']}: {room['participants']['total']} participants"
            )

        # Create a room with auto-generated ID
        logger.info("\n=== Creating room with auto-generated ID ===")
        room_id_1 = await client.create_room()
        logger.info(f"Created room: {room_id_1}")

        # Create a room with custom ID
        logger.info("\n=== Creating room with custom ID ===")
        custom_room_id = "my-custom-room-123"
        room_id_2 = await client.create_room(custom_room_id)
        logger.info(f"Created custom room: {room_id_2}")

        # Get room info
        logger.info(f"\n=== Getting info for room {room_id_1} ===")
        room_info = await client.get_room_info(room_id_1)
        logger.info(f"Room info: {room_info}")

        # Get room state
        logger.info(f"\n=== Getting state for room {room_id_1} ===")
        room_state = await client.get_room_state(room_id_1)
        logger.info(f"Room state: {room_state}")

        # List rooms again to see our new ones
        logger.info("\n=== Listing rooms after creation ===")
        rooms = await client.list_rooms()
        logger.info(f"Now have {len(rooms)} rooms:")
        for room in rooms:
            logger.info(
                f"  - {room['id']}: {room['participants']['total']} participants"
            )

        # Clean up - delete the rooms we created
        logger.info("\n=== Cleaning up ===")

        success_1 = await client.delete_room(room_id_1)
        logger.info(f"Deleted room {room_id_1}: {success_1}")

        success_2 = await client.delete_room(room_id_2)
        logger.info(f"Deleted room {room_id_2}: {success_2}")

        # Try to delete non-existent room
        success_3 = await client.delete_room("non-existent-room")
        logger.info(f"Tried to delete non-existent room: {success_3}")

        # List final rooms
        logger.info("\n=== Final room list ===")
        rooms = await client.list_rooms()
        logger.info(f"Final count: {len(rooms)} rooms")

        logger.info("\nRoom management example completed!")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
