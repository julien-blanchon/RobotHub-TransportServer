import logging

from fastapi import APIRouter, HTTPException, WebSocket

from .core import VideoCore
from .models import (
    CreateRoomRequest,
    ParticipantRole,
    RecoveryPolicy,
    VideoEncoding,
    WebRTCSignalRequest,
)

logger = logging.getLogger(__name__)

video_router = APIRouter(prefix="/video", tags=["video"])
video_core = VideoCore()


# ============= WORKSPACE-SCOPED ENDPOINTS =============


@video_router.get("/workspaces/{workspace_id}/rooms")
async def list_rooms_in_workspace(workspace_id: str):
    """List all video rooms in a workspace"""
    rooms = video_core.list_rooms(workspace_id)
    return {
        "success": True,
        "workspace_id": workspace_id,
        "rooms": rooms,
        "total": len(rooms),
    }


@video_router.post("/workspaces/{workspace_id}/rooms")
async def create_room_in_workspace(
    workspace_id: str, request: CreateRoomRequest | None = None
):
    """Create a new video room in a workspace"""
    room_id = None
    config = None
    recovery_config = None

    if request:
        room_id = request.room_id
        config = request.config
        recovery_config = request.recovery_config

    # Create room with explicit workspace_id
    created_workspace_id, room_id = video_core.create_room(
        workspace_id, room_id, config, recovery_config
    )

    return {
        "success": True,
        "workspace_id": created_workspace_id,
        "room_id": room_id,
        "message": f"Video room {room_id} created successfully in workspace {created_workspace_id}",
    }


@video_router.get("/workspaces/{workspace_id}/rooms/{room_id}")
async def get_room_in_workspace(workspace_id: str, room_id: str):
    """Get room details from a workspace"""
    room_info = video_core.get_room_info(workspace_id, room_id)
    if "error" in room_info:
        raise HTTPException(status_code=404, detail="Room not found")

    return {"success": True, "workspace_id": workspace_id, "room": room_info}


@video_router.delete("/workspaces/{workspace_id}/rooms/{room_id}")
async def delete_room_in_workspace(workspace_id: str, room_id: str):
    """Delete a video room from a workspace"""
    if video_core.delete_room(workspace_id, room_id):
        return {
            "success": True,
            "workspace_id": workspace_id,
            "message": f"Room {room_id} deleted successfully from workspace {workspace_id}",
        }
    raise HTTPException(status_code=404, detail="Room not found")


@video_router.get("/workspaces/{workspace_id}/rooms/{room_id}/state")
async def get_room_state_in_workspace(workspace_id: str, room_id: str):
    """Get current room state from a workspace"""
    state = video_core.get_room_state(workspace_id, room_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail="Room not found")

    return {"success": True, "workspace_id": workspace_id, "state": state}


@video_router.post("/workspaces/{workspace_id}/rooms/{room_id}/webrtc/signal")
async def handle_webrtc_signal_in_workspace(
    workspace_id: str, room_id: str, signal: WebRTCSignalRequest
):
    """Handle WebRTC signaling (offer, answer, ice) in a workspace"""
    try:
        # Get the participant's role from the room
        room = video_core._get_room(workspace_id, room_id)
        participant_role: ParticipantRole | None = None

        if room:
            if room.producer == signal.client_id:
                participant_role = ParticipantRole.PRODUCER
            elif signal.client_id in room.consumers:
                participant_role = ParticipantRole.CONSUMER

        logger.info(
            f"🔧 WebRTC signal from {signal.client_id} (role: {participant_role}) in workspace {workspace_id}, room {room_id}"
        )

        response = await video_core.handle_webrtc_signal(
            workspace_id, room_id, signal.client_id, signal.message, participant_role
        )

    except ValueError as e:
        raise HTTPException(status_code=400) from e
    except Exception as e:
        raise HTTPException(status_code=500) from e
    else:
        if response:
            return {"success": True, "workspace_id": workspace_id, "response": response}
        return {
            "success": True,
            "workspace_id": workspace_id,
            "message": "Signal processed",
        }


@video_router.websocket("/workspaces/{workspace_id}/rooms/{room_id}/ws")
async def websocket_endpoint_in_workspace(
    websocket: WebSocket, workspace_id: str, room_id: str
):
    """WebSocket connection for room management and heartbeat in a workspace"""
    await video_core.handle_websocket(websocket, workspace_id, room_id)


# ============= SERVICE STATUS ENDPOINTS =============


@video_router.get("/status")
async def get_status():
    """Get video service status"""
    total_workspaces = len(video_core.workspaces)
    total_rooms = sum(len(rooms) for rooms in video_core.workspaces.values())
    cleanup_info = video_core.get_cleanup_status()

    return {
        "service": "video",
        "status": "active",
        "workspaces_count": total_workspaces,
        "rooms_count": total_rooms,
        "webrtc_connections_count": len(video_core.webrtc_connections),
        "websocket_connections_count": len(video_core.websocket_connections),
        "version": "2.0.0",
        "supported_roles": [role.value for role in ParticipantRole],
        "supported_encodings": [encoding.value for encoding in VideoEncoding],
        "recovery_policies": [policy.value for policy in RecoveryPolicy],
        "cleanup": {
            "enabled": cleanup_info["cleanup_enabled"],
            "inactivity_timeout_hours": cleanup_info["inactivity_timeout_minutes"] / 60,
            "cleanup_interval_minutes": cleanup_info["cleanup_interval_minutes"],
        },
    }


@video_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video"}


@video_router.get("/cleanup/status")
async def get_cleanup_status():
    """Get cleanup system status and room information"""
    status = video_core.get_cleanup_status()
    return {"success": True, "cleanup_status": status}


@video_router.post("/cleanup/manual")
async def trigger_manual_cleanup():
    """Manually trigger room cleanup"""
    result = await video_core.manual_cleanup()
    return {"success": True, "cleanup_result": result}


@video_router.get("/")
async def video_status():
    """Video service main endpoint"""
    return {
        "status": "active",
        "service": "video",
        "message": "Video service running with workspace-scoped room-based WebRTC streaming",
        "version": "2.0.0",
        "architecture": "workspace/producer/consumer rooms",
        "endpoints": [
            "/video/workspaces/{workspace_id}/rooms - List all video rooms in workspace",
            "/video/workspaces/{workspace_id}/rooms/{room_id} - Get room details",
            "/video/workspaces/{workspace_id}/rooms/{room_id}/webrtc/signal - WebRTC signaling",
            "/video/workspaces/{workspace_id}/rooms/{room_id}/ws - WebSocket connection",
            "/video/status - Service status",
            "/video/cleanup/status - Cleanup system status",
            "/video/cleanup/manual - Manual cleanup trigger",
        ],
    }
