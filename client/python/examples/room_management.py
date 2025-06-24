#!/usr/bin/env python3
"""
Room Management Example - RobotHub TransportServer

This example demonstrates:
- Listing rooms in a workspace
- Creating rooms (with and without custom IDs)
- Getting room information
- Getting room state
- Deleting rooms
"""

import asyncio
import logging

from transport_server_client import RoboticsClientCore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Room management example."""
    # Create a basic client for API operations
    client = RoboticsClientCore("http://localhost:8000")

    try:
        # Generate a workspace ID for this demo
        workspace_id = client._generate_workspace_id()
        logger.info(f"Using workspace: {workspace_id}")

        # List existing rooms in this workspace
        logger.info("=== Listing existing rooms ===")
        rooms = await client.list_rooms(workspace_id)
        logger.info(f"Found {len(rooms)} rooms in workspace:")
        for room in rooms:
            logger.info(
                f"  - {room['id']}: {room['participants']['total']} participants"
            )

        # Create a room with auto-generated ID
        logger.info("\n=== Creating room with auto-generated ID ===")
        workspace_id_1, room_id_1 = await client.create_room()
        logger.info(f"Created room: {room_id_1}")
        logger.info(f"In workspace: {workspace_id_1}")

        # Create a room with custom ID in our workspace
        logger.info("\n=== Creating room with custom ID ===")
        custom_room_id = "my-custom-room-123"
        workspace_id_2, room_id_2 = await client.create_room(
            workspace_id, custom_room_id
        )
        logger.info(f"Created custom room: {room_id_2}")
        logger.info(f"In workspace: {workspace_id_2}")

        # Get room info
        logger.info(f"\n=== Getting info for room {room_id_1} ===")
        room_info = await client.get_room_info(workspace_id_1, room_id_1)
        logger.info(f"Room info: {room_info}")

        # Get room state
        logger.info(f"\n=== Getting state for room {room_id_1} ===")
        room_state = await client.get_room_state(workspace_id_1, room_id_1)
        logger.info(f"Room state: {room_state}")

        # List rooms again to see our new ones
        logger.info(f"\n=== Listing rooms in workspace {workspace_id} ===")
        rooms = await client.list_rooms(workspace_id)
        logger.info(f"Now have {len(rooms)} rooms:")
        for room in rooms:
            logger.info(
                f"  - {room['id']}: {room['participants']['total']} participants"
            )

        # Clean up - delete the rooms we created
        logger.info("\n=== Cleaning up ===")

        success_1 = await client.delete_room(workspace_id_1, room_id_1)
        logger.info(f"Deleted room {room_id_1}: {success_1}")

        success_2 = await client.delete_room(workspace_id_2, room_id_2)
        logger.info(f"Deleted room {room_id_2}: {success_2}")

        # Try to delete non-existent room
        success_3 = await client.delete_room(workspace_id, "non-existent-room")
        logger.info(f"Tried to delete non-existent room: {success_3}")

        # List final rooms
        logger.info(f"\n=== Final room list in workspace {workspace_id} ===")
        rooms = await client.list_rooms(workspace_id)
        logger.info(f"Final count: {len(rooms)} rooms")

        logger.info("\nRoom management example completed!")

    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
