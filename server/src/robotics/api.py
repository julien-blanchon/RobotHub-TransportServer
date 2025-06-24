from fastapi import APIRouter, HTTPException, WebSocket

from .core import RoboticsCore
from .models import (
    CreateRoomRequest,
    JointCommand,
    ParticipantRole,
)

# ============= SIMPLIFIED API =============

robotics_router = APIRouter(prefix="/robotics", tags=["robotics"])
robotics_core = RoboticsCore()


# ============= CONVENIENT ROOM ENDPOINTS =============


# Legacy endpoint for backward compatibility - creates random workspace
@robotics_router.get("/rooms")
async def list_rooms_legacy():
    """List all robotics rooms (legacy - requires workspace)"""
    raise HTTPException(
        status_code=400,
        detail="Workspace ID required. Use /workspaces/{workspace_id}/rooms instead",
    )


@robotics_router.get("/workspaces/{workspace_id}/rooms")
async def list_rooms(workspace_id: str):
    """List all robotics rooms in a workspace"""
    return {
        "success": True,
        "workspace_id": workspace_id,
        "rooms": robotics_core.list_rooms(workspace_id),
        "total": len(robotics_core.list_rooms(workspace_id)),
    }


# Legacy endpoint for backward compatibility - creates random workspace
@robotics_router.post("/rooms")
async def create_room_legacy(request: CreateRoomRequest | None = None):
    """Create a new robotics room (legacy - creates random workspace)"""
    workspace_id = None
    room_id = None
    if request:
        workspace_id = request.workspace_id
        room_id = request.room_id

    workspace_id, room_id = robotics_core.create_room(workspace_id, room_id)

    return {
        "success": True,
        "workspace_id": workspace_id,
        "room_id": room_id,
        "message": f"Room {room_id} created successfully in workspace {workspace_id}",
    }


@robotics_router.post("/workspaces/{workspace_id}/rooms")
async def create_room(workspace_id: str, request: CreateRoomRequest | None = None):
    """Create a new robotics room in a workspace"""
    room_id = None
    if request and hasattr(request, "room_id"):
        room_id = request.room_id

    actual_workspace_id, room_id = robotics_core.create_room(workspace_id, room_id)

    return {
        "success": True,
        "workspace_id": actual_workspace_id,
        "room_id": room_id,
        "message": f"Room {room_id} created successfully in workspace {actual_workspace_id}",
    }


@robotics_router.get("/workspaces/{workspace_id}/rooms/{room_id}")
async def get_room(workspace_id: str, room_id: str):
    """Get room details"""
    room_info = robotics_core.get_room_info(workspace_id, room_id)
    if "error" in room_info:
        raise HTTPException(status_code=404, detail="Room not found")

    return {"success": True, "room": room_info}


@robotics_router.delete("/workspaces/{workspace_id}/rooms/{room_id}")
async def delete_room(workspace_id: str, room_id: str):
    """Delete a robotics room"""
    if robotics_core.delete_room(workspace_id, room_id):
        return {
            "success": True,
            "message": f"Room {room_id} deleted successfully from workspace {workspace_id}",
        }
    raise HTTPException(status_code=404, detail="Room not found")


@robotics_router.get("/workspaces/{workspace_id}/rooms/{room_id}/state")
async def get_room_state(workspace_id: str, room_id: str):
    """Get current room state with joints and participants"""
    state = robotics_core.get_room_state(workspace_id, room_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail="Room not found")

    return {"success": True, "state": state}


# ============= CONTROL ENDPOINTS =============


@robotics_router.post("/workspaces/{workspace_id}/rooms/{room_id}/command")
async def send_command(workspace_id: str, room_id: str, command: JointCommand):
    """Send joint commands to a room"""
    room_info = robotics_core.get_room_info(workspace_id, room_id)
    if "error" in room_info:
        raise HTTPException(status_code=404, detail="Room not found")

    try:
        joints_data = [
            {"name": j.name, "value": j.value, "speed": j.speed} for j in command.joints
        ]
        changed = await robotics_core.send_command_to_room(
            workspace_id, room_id, joints_data
        )
    except ValueError as e:
        raise HTTPException(status_code=404) from e
    else:
        return {
            "success": True,
            "workspace_id": workspace_id,
            "room_id": room_id,
            "joints_updated": changed,
            "message": "Commands sent successfully",
        }


# ============= UTILITY ENDPOINTS =============


@robotics_router.get("/status")
async def get_status():
    """Get system status"""
    stats = robotics_core.get_connection_stats()
    return {
        "service": "robotics",
        "status": "active",
        "workspaces_count": stats["total_workspaces"],
        "rooms_count": stats["total_rooms"],
        "connections_count": stats["total_connections"],
        "version": "2.0.0",
        "supported_roles": [role.value for role in ParticipantRole],
        "supported_robot_types": ["so-arm100", "generic"],
    }


@robotics_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "robotics"}


# ============= WEBSOCKET ENDPOINT =============


@robotics_router.websocket("/workspaces/{workspace_id}/rooms/{room_id}/ws")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str, room_id: str):
    """WebSocket connection for real-time room communication"""
    await robotics_core.handle_websocket(websocket, workspace_id, room_id)
