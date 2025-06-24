import asyncio

import pytest
import pytest_asyncio
from lerobot_arena_client import RoboticsConsumer, RoboticsProducer

# Default server URL for tests
TEST_SERVER_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def producer():
    """Create a RoboticsProducer instance for testing."""
    client = RoboticsProducer(TEST_SERVER_URL)
    yield client
    if client.is_connected():
        await client.disconnect()


@pytest_asyncio.fixture
async def consumer():
    """Create a RoboticsConsumer instance for testing."""
    client = RoboticsConsumer(TEST_SERVER_URL)
    yield client
    if client.is_connected():
        await client.disconnect()


@pytest_asyncio.fixture
async def test_room(producer):
    """Create a test room and clean up after test."""
    room_id = await producer.create_room()
    yield room_id
    # Cleanup: delete the room after test
    try:
        await producer.delete_room(room_id)
    except Exception:
        pass  # Room might already be deleted


@pytest_asyncio.fixture
async def connected_producer(producer, test_room):
    """Create a connected producer in a test room."""
    await producer.connect(test_room)
    yield producer, test_room


@pytest_asyncio.fixture
async def connected_consumer(consumer, test_room):
    """Create a connected consumer in a test room."""
    await consumer.connect(test_room)
    yield consumer, test_room


@pytest_asyncio.fixture
async def producer_consumer_pair(producer, consumer, test_room):
    """Create a connected producer-consumer pair in the same room."""
    await producer.connect(test_room)
    await consumer.connect(test_room)
    yield producer, consumer, test_room
