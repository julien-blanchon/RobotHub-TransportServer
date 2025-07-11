import pytest
import pytest_asyncio
from transport_server_client import RoboticsProducer


@pytest_asyncio.fixture
async def producer():
    """Create a producer for REST API testing."""
    client = RoboticsProducer("http://localhost:8000")
    yield client


class TestRestAPI:
    """Test REST API functionality."""

    @pytest.mark.asyncio
    async def test_list_rooms_empty(self, producer):
        """Test listing rooms when no rooms exist."""
        # Use a temporary workspace ID
        workspace_id = producer.generate_workspace_id()
        rooms = await producer.list_rooms(workspace_id)
        assert isinstance(rooms, list)

    @pytest.mark.asyncio
    async def test_create_room(self, producer):
        """Test creating a room."""
        workspace_id, room_id = await producer.create_room()
        assert isinstance(workspace_id, str)
        assert isinstance(room_id, str)
        assert len(workspace_id) > 0
        assert len(room_id) > 0

        # Cleanup
        await producer.delete_room(workspace_id, room_id)

    @pytest.mark.asyncio
    async def test_create_room_with_id(self, producer):
        """Test creating a room with specific ID."""
        custom_room_id = "test-room-123"
        custom_workspace_id = "test-workspace-456"
        workspace_id, room_id = await producer.create_room(
            custom_workspace_id, custom_room_id
        )
        assert workspace_id == custom_workspace_id
        assert room_id == custom_room_id

        # Cleanup
        await producer.delete_room(workspace_id, room_id)

    @pytest.mark.asyncio
    async def test_list_rooms_with_rooms(self, producer):
        """Test listing rooms when rooms exist."""
        # Create a test room
        workspace_id, room_id = await producer.create_room()

        try:
            rooms = await producer.list_rooms(workspace_id)
            assert isinstance(rooms, list)
            assert len(rooms) >= 1

            # Check if our room is in the list
            room_ids = [room["id"] for room in rooms]
            assert room_id in room_ids

            # Verify room structure
            test_room = next(room for room in rooms if room["id"] == room_id)
            assert "participants" in test_room
            assert "joints_count" in test_room

        finally:
            await producer.delete_room(workspace_id, room_id)

    @pytest.mark.asyncio
    async def test_get_room_info(self, producer):
        """Test getting room information."""
        workspace_id, room_id = await producer.create_room()

        try:
            room_info = await producer.get_room_info(workspace_id, room_id)
            assert isinstance(room_info, dict)
            assert room_info["id"] == room_id
            assert room_info["workspace_id"] == workspace_id
            assert "participants" in room_info
            assert "joints_count" in room_info
            assert "has_producer" in room_info
            assert "active_consumers" in room_info

        finally:
            await producer.delete_room(workspace_id, room_id)

    @pytest.mark.asyncio
    async def test_get_room_state(self, producer):
        """Test getting room state."""
        workspace_id, room_id = await producer.create_room()

        try:
            room_state = await producer.get_room_state(workspace_id, room_id)
            assert isinstance(room_state, dict)
            assert "room_id" in room_state
            assert "workspace_id" in room_state
            assert "joints" in room_state
            assert "participants" in room_state
            assert "timestamp" in room_state
            assert room_state["room_id"] == room_id
            assert room_state["workspace_id"] == workspace_id

        finally:
            await producer.delete_room(workspace_id, room_id)

    @pytest.mark.asyncio
    async def test_delete_room(self, producer):
        """Test deleting a room."""
        workspace_id, room_id = await producer.create_room()

        # Verify room exists
        rooms_before = await producer.list_rooms(workspace_id)
        room_ids_before = [room["id"] for room in rooms_before]
        assert room_id in room_ids_before

        # Delete room
        success = await producer.delete_room(workspace_id, room_id)
        assert success is True

        # Verify room is deleted
        rooms_after = await producer.list_rooms(workspace_id)
        room_ids_after = [room["id"] for room in rooms_after]
        assert room_id not in room_ids_after

    @pytest.mark.asyncio
    async def test_delete_nonexistent_room(self, producer):
        """Test deleting a room that doesn't exist."""
        workspace_id = producer.generate_workspace_id()
        fake_room_id = "nonexistent-room-id"
        success = await producer.delete_room(workspace_id, fake_room_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_room_info_nonexistent(self, producer):
        """Test getting info for a room that doesn't exist."""
        workspace_id = producer.generate_workspace_id()
        fake_room_id = "nonexistent-room-id"

        # This should raise an exception or return error info
        try:
            await producer.get_room_info(workspace_id, fake_room_id)
            # If no exception, check for error in response
        except Exception:
            # Expected behavior for nonexistent room
            pass

    @pytest.mark.asyncio
    async def test_get_room_state_nonexistent(self, producer):
        """Test getting state for a room that doesn't exist."""
        workspace_id = producer.generate_workspace_id()
        fake_room_id = "nonexistent-room-id"

        # This should raise an exception or return error info
        try:
            await producer.get_room_state(workspace_id, fake_room_id)
            # If no exception, check for error in response
        except Exception:
            # Expected behavior for nonexistent room
            pass
