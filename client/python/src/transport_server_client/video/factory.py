"""
Factory functions for creating RobotHub TransportServer video clients
"""

from .consumer import VideoConsumer
from .producer import VideoProducer
from .types import ClientOptions, ParticipantRole


def create_client(
    role: ParticipantRole,
    base_url: str,
    options: ClientOptions | None = None,
) -> "VideoProducer | VideoConsumer":
    """Factory function to create the appropriate client based on role"""
    if role == ParticipantRole.PRODUCER:
        return VideoProducer(base_url, options)
    if role == ParticipantRole.CONSUMER:
        return VideoConsumer(base_url, options)
    msg = f"Invalid role: {role}. Must be 'producer' or 'consumer'"
    raise ValueError(msg)


async def create_producer_client(
    base_url: str,
    workspace_id: str | None = None,
    room_id: str | None = None,
    participant_id: str | None = None,
    options: ClientOptions | None = None,
) -> VideoProducer:
    """Create and connect a producer client"""
    producer = VideoProducer(base_url, options)

    workspace_id, room_id = await producer.create_room(workspace_id, room_id)
    connected = await producer.connect(workspace_id, room_id, participant_id)

    if not connected:
        msg = "Failed to connect as video producer"
        raise ValueError(msg)

    return producer


async def create_consumer_client(
    workspace_id: str,
    room_id: str,
    base_url: str,
    participant_id: str | None = None,
    options: ClientOptions | None = None,
) -> VideoConsumer:
    """Create and connect a consumer client"""
    consumer = VideoConsumer(base_url, options)
    connected = await consumer.connect(workspace_id, room_id, participant_id)

    if not connected:
        msg = "Failed to connect as video consumer"
        raise ValueError(msg)

    return consumer
