import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import WebSocket, WebSocketDisconnect
from typing_extensions import TypedDict

from .models import MessageType, ParticipantRole

logger = logging.getLogger(__name__)


class ConnectionMetadata(TypedDict):
    """Connection metadata with proper typing"""

    workspace_id: str
    room_id: str
    participant_id: str
    role: ParticipantRole
    connected_at: datetime
    last_activity: datetime
    message_count: int


# ============= SIMPLIFIED ROOM SYSTEM =============


class RoboticsRoom:
    """Simple robotics room with producer/consumer pattern"""

    def __init__(self, room_id: str, workspace_id: str):
        self.id = room_id
        self.workspace_id = workspace_id

        # Participants
        self.producer: str | None = None
        self.consumers: list[str] = []

        # State
        self.joints: dict[str, float] = {}

        # Activity tracking
        self.created_at = datetime.now(tz=UTC)
        self.last_activity = datetime.now(tz=UTC)


class RoboticsCore:
    """Core robotics system - simplified and merged with workspace support"""

    def __init__(self):
        # Nested structure: workspace_id -> room_id -> RoboticsRoom
        self.workspaces: dict[str, dict[str, RoboticsRoom]] = {}
        self.connections: dict[str, WebSocket] = {}  # participant_id -> websocket
        self.connection_metadata: dict[
            str, ConnectionMetadata
        ] = {}  # participant_id -> metadata

        # Cleanup configuration
        self.inactivity_timeout = timedelta(hours=1)  # 1 hour of inactivity
        self.cleanup_interval = timedelta(minutes=15)  # Check every 15 minutes

        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start the background cleanup task"""
        import asyncio

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval.total_seconds())
                    await self._cleanup_inactive_rooms()
                except Exception:
                    logger.exception("Error in cleanup task")

        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
            logger.info("Started robotics room cleanup task")
        except RuntimeError:
            # No event loop running yet, cleanup will start when first room is created
            logger.info("No event loop running, cleanup task will start later")

    async def _cleanup_inactive_rooms(self):
        """Remove rooms that have been inactive for more than the timeout period"""
        current_time = datetime.now(tz=UTC)
        rooms_to_remove = []

        for workspace_id, rooms in self.workspaces.items():
            for room_id, room in rooms.items():
                # Check if room has any active connections
                has_active_connections = False
                room_last_activity = room.last_activity

                # Check all connections for this room to find most recent activity
                for metadata in self.connection_metadata.values():
                    if (
                        metadata["workspace_id"] == workspace_id
                        and metadata["room_id"] == room_id
                    ):
                        has_active_connections = True
                        room_last_activity = max(
                            room_last_activity, metadata["last_activity"]
                        )

                # If no active connections, use room's last activity
                if not has_active_connections:
                    time_since_activity = current_time - room_last_activity

                    if time_since_activity > self.inactivity_timeout:
                        rooms_to_remove.append((workspace_id, room_id))
                        logger.info(
                            f"Marking room {room_id} in workspace {workspace_id} for cleanup "
                            f"(inactive for {time_since_activity})"
                        )

        # Remove inactive rooms
        for workspace_id, room_id in rooms_to_remove:
            if self.delete_room(workspace_id, room_id):
                logger.info(
                    f"Auto-removed inactive room {room_id} from workspace {workspace_id}"
                )

        if rooms_to_remove:
            logger.info(f"Cleaned up {len(rooms_to_remove)} inactive robotics rooms")

    def _update_room_activity(self, workspace_id: str, room_id: str):
        """Update the last activity timestamp for a room"""
        room = self._get_room(workspace_id, room_id)
        if room:
            room.last_activity = datetime.now(tz=UTC)

    # ============= ROOM MANAGEMENT =============

    def create_room(
        self, workspace_id: str | None = None, room_id: str | None = None
    ) -> tuple[str, str]:
        """Create a new room and return (workspace_id, room_id)"""
        workspace_id = workspace_id or str(uuid.uuid4())
        room_id = room_id or str(uuid.uuid4())

        # Initialize workspace if it doesn't exist
        if workspace_id not in self.workspaces:
            self.workspaces[workspace_id] = {}

        room = RoboticsRoom(room_id, workspace_id)
        self.workspaces[workspace_id][room_id] = room

        # Start cleanup task if not already running
        if self._cleanup_task is None:
            self._start_cleanup_task()

        logger.info(f"Created room {room_id} in workspace {workspace_id}")
        return workspace_id, room_id

    def list_rooms(self, workspace_id: str) -> list[dict]:
        """List all rooms in a specific workspace"""
        if workspace_id not in self.workspaces:
            return []

        return [
            {
                "id": room.id,
                "workspace_id": room.workspace_id,
                "participants": {
                    "producer": room.producer,
                    "consumers": room.consumers,
                    "total": len(room.consumers) + (1 if room.producer else 0),
                },
                "joints_count": len(room.joints),
            }
            for room in self.workspaces[workspace_id].values()
        ]

    def delete_room(self, workspace_id: str, room_id: str) -> bool:
        """Delete a room from a workspace"""
        if (
            workspace_id not in self.workspaces
            or room_id not in self.workspaces[workspace_id]
        ):
            return False

        room = self.workspaces[workspace_id][room_id]

        # Disconnect all participants
        for consumer_id in room.consumers[:]:
            self.leave_room(workspace_id, room_id, consumer_id)
        if room.producer:
            self.leave_room(workspace_id, room_id, room.producer)

        del self.workspaces[workspace_id][room_id]
        logger.info(f"Deleted room {room_id} from workspace {workspace_id}")
        return True

    def get_room_state(self, workspace_id: str, room_id: str) -> dict:
        """Get detailed room state"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return {"error": "Room not found"}

        return {
            "room_id": room_id,
            "workspace_id": workspace_id,
            "joints": room.joints,
            "participants": {
                "producer": room.producer,
                "consumers": room.consumers,
                "total": len(room.consumers) + (1 if room.producer else 0),
            },
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

    def get_room_info(self, workspace_id: str, room_id: str) -> dict:
        """Get basic room info"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return {"error": "Room not found"}

        return {
            "id": room.id,
            "workspace_id": room.workspace_id,
            "participants": {
                "producer": room.producer,
                "consumers": room.consumers,
                "total": len(room.consumers) + (1 if room.producer else 0),
            },
            "joints_count": len(room.joints),
            "has_producer": room.producer is not None,
            "active_consumers": len(room.consumers),
        }

    def _get_room(self, workspace_id: str, room_id: str) -> RoboticsRoom | None:
        """Get room by workspace and room ID"""
        if workspace_id not in self.workspaces:
            return None
        return self.workspaces[workspace_id].get(room_id)

    # ============= PARTICIPANT MANAGEMENT =============

    def join_room(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
    ) -> bool:
        """Join room as producer or consumer"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return False

        if role == ParticipantRole.PRODUCER:
            if room.producer is None:
                room.producer = participant_id
                self._update_room_activity(workspace_id, room_id)
                logger.info(
                    f"Producer {participant_id} joined room {room_id} in workspace {workspace_id}"
                )
                return True
            # Room already has a producer, reject the new one
            logger.warning(
                f"Producer {participant_id} failed to join room {room_id} - room already has producer {room.producer}"
            )
            return False

        if role == ParticipantRole.CONSUMER:
            if participant_id not in room.consumers:
                room.consumers.append(participant_id)
                self._update_room_activity(workspace_id, room_id)
                logger.info(
                    f"Consumer {participant_id} joined room {room_id} in workspace {workspace_id}"
                )
                return True
            return False

        return False

    def leave_room(self, workspace_id: str, room_id: str, participant_id: str):
        """Leave room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        if room.producer == participant_id:
            room.producer = None
            logger.info(
                f"Producer {participant_id} left room {room_id} in workspace {workspace_id}"
            )
        elif participant_id in room.consumers:
            room.consumers.remove(participant_id)
            logger.info(
                f"Consumer {participant_id} left room {room_id} in workspace {workspace_id}"
            )

    # ============= JOINT CONTROL =============

    def update_joints(
        self, workspace_id: str, room_id: str, joint_updates: list[dict]
    ) -> list[dict]:
        room = self._get_room(workspace_id, room_id)
        if not room:
            msg = f"Room {room_id} not found in workspace {workspace_id}"
            raise ValueError(msg)

        changed_joints = []
        for joint in joint_updates:
            name = joint["name"]
            value = joint["value"]

            # Only track actual changes
            if room.joints.get(name) != value:
                room.joints[name] = value
                changed_joints.append(joint)

        # Update room activity if there were changes
        if changed_joints:
            self._update_room_activity(workspace_id, room_id)

        return changed_joints

    # ============= WEBSOCKET HANDLING =============

    async def handle_websocket(
        self, websocket: WebSocket, workspace_id: str, room_id: str
    ):
        """Handle WebSocket connection"""
        await websocket.accept()

        participant_id: str | None = None
        role: ParticipantRole | None = None

        try:
            # Get join message
            data = await websocket.receive_text()
            join_msg = json.loads(data)

            participant_id = join_msg["participant_id"]
            role = ParticipantRole(join_msg["role"])

            # Join room
            if not self.join_room(workspace_id, room_id, participant_id, role):
                await websocket.send_text(
                    json.dumps({
                        "type": MessageType.ERROR.value,
                        "message": "Cannot join room",
                    })
                )
                await websocket.close()
                return

            self.connections[participant_id] = websocket

            # Store connection metadata
            self.connection_metadata[participant_id] = ConnectionMetadata(
                workspace_id=workspace_id,
                room_id=room_id,
                participant_id=participant_id,
                role=role,
                connected_at=datetime.now(tz=UTC),
                last_activity=datetime.now(tz=UTC),
                message_count=0,
            )

            # Send current state to consumer
            if role == ParticipantRole.CONSUMER:
                room = self._get_room(workspace_id, room_id)
                if room:
                    await websocket.send_text(
                        json.dumps({
                            "type": MessageType.STATE_SYNC.value,
                            "data": room.joints,
                            "timestamp": datetime.now(tz=UTC).isoformat(),
                        })
                    )

            # Send join confirmation
            await websocket.send_text(
                json.dumps({
                    "type": MessageType.JOINED.value,
                    "room_id": room_id,
                    "workspace_id": workspace_id,
                    "role": role.value,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                })
            )

            # Handle messages
            async for message in websocket.iter_text():
                try:
                    msg = json.loads(message)
                    await self._handle_message(
                        workspace_id, room_id, participant_id, role, msg
                    )
                except json.JSONDecodeError:
                    logger.exception(f"Invalid JSON from {participant_id}")
                except Exception:
                    logger.exception("Message error")

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {participant_id}")
        except Exception:
            logger.exception("WebSocket error")
        finally:
            # Cleanup
            if participant_id:
                metadata = self.connection_metadata.get(participant_id)
                if metadata:
                    self.leave_room(
                        metadata["workspace_id"], metadata["room_id"], participant_id
                    )
                if participant_id in self.connections:
                    del self.connections[participant_id]
                if participant_id in self.connection_metadata:
                    del self.connection_metadata[participant_id]

    async def _handle_message(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
        message: dict,
    ):
        """Handle incoming WebSocket message with structured handlers"""
        # Update activity tracking
        if participant_id in self.connection_metadata:
            self.connection_metadata[participant_id]["last_activity"] = datetime.now(
                tz=UTC
            )
            self.connection_metadata[participant_id]["message_count"] += 1

        # Update room activity
        self._update_room_activity(workspace_id, room_id)

        try:
            msg_type = MessageType(message.get("type"))
        except ValueError:
            logger.warning(
                f"Unknown message type from {participant_id}: {message.get('type')}"
            )
            await self._handle_error(
                participant_id, f"Unknown message type: {message.get('type')}"
            )
            return

        # Dispatch to specific handlers
        if msg_type == MessageType.JOINT_UPDATE:
            await self._handle_joint_update(
                workspace_id, room_id, participant_id, role, message
            )
        elif msg_type == MessageType.HEARTBEAT:
            await self._handle_heartbeat(participant_id)
        elif msg_type == MessageType.EMERGENCY_STOP:
            await self._handle_emergency_stop(
                workspace_id, room_id, participant_id, message
            )
        else:
            logger.warning(f"Unhandled message type {msg_type} from {participant_id}")

    # ============= STRUCTURED MESSAGE HANDLERS =============

    async def _handle_joint_update(
        self,
        workspace_id: str,
        room_id: str,
        participant_id: str,
        role: ParticipantRole,
        message: dict,
    ):
        """Handle joint update commands from producers"""
        if role != ParticipantRole.PRODUCER:
            logger.warning(
                f"Non-producer {participant_id} attempted to send joint update"
            )
            return

        joints = message.get("data", [])
        if not joints:
            logger.warning(f"Empty joint data from producer {participant_id}")
            return

        try:
            changed_joints = self.update_joints(workspace_id, room_id, joints)

            if changed_joints:
                await self._broadcast_to_consumers(
                    workspace_id,
                    room_id,
                    {
                        "type": MessageType.JOINT_UPDATE.value,
                        "data": changed_joints,
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "source": participant_id,
                    },
                )
                logger.debug(
                    f"Producer {participant_id} sent {len(changed_joints)} joint updates"
                )
        except Exception:
            logger.exception(f"Error processing joint update from {participant_id}")
            await self._handle_error(participant_id, "Failed to process joint update")

    async def _handle_heartbeat(self, participant_id: str):
        """Handle heartbeat messages"""
        try:
            await self._send_to_participant(
                participant_id,
                {
                    "type": MessageType.HEARTBEAT_ACK.value,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                },
            )
            logger.debug(f"Heartbeat acknowledged for {participant_id}")
        except Exception:
            logger.exception(f"Error handling heartbeat from {participant_id}")

    async def _handle_emergency_stop(
        self, workspace_id: str, room_id: str, participant_id: str, message: dict
    ):
        """Handle emergency stop messages"""
        try:
            reason = message.get("reason", f"Emergency stop from {participant_id}")

            emergency_message = {
                "type": MessageType.EMERGENCY_STOP.value,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "reason": reason,
                "source": participant_id,
            }

            # Broadcast to all participants in room
            await self._broadcast_to_all_participants(
                workspace_id, room_id, emergency_message
            )
            logger.warning(
                f"🚨 Emergency stop triggered by {participant_id} in room {room_id} (workspace {workspace_id})"
            )

        except Exception:
            logger.exception(f"Error handling emergency stop from {participant_id}")

    async def _handle_error(self, participant_id: str, error_message: str):
        """Send error message to participant"""
        try:
            await self._send_to_participant(
                participant_id,
                {
                    "type": MessageType.ERROR.value,
                    "message": error_message,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                },
            )
        except Exception:
            logger.exception(f"Error sending error message to {participant_id}")

    async def _broadcast_to_consumers(
        self, workspace_id: str, room_id: str, message: dict
    ):
        """Send message to all consumers in room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        message_text = json.dumps(message)
        failed = []

        for consumer_id in room.consumers:
            if consumer_id in self.connections:
                try:
                    await self.connections[consumer_id].send_text(message_text)
                except Exception:
                    logger.exception(f"Error sending message to {consumer_id}")
                    failed.append(consumer_id)

        # Cleanup failed connections
        for consumer_id in failed:
            room.consumers.remove(consumer_id)
            if consumer_id in self.connections:
                del self.connections[consumer_id]
            if consumer_id in self.connection_metadata:
                del self.connection_metadata[consumer_id]

    async def _broadcast_to_all_participants(
        self, workspace_id: str, room_id: str, message: dict
    ):
        """Send message to all participants (producer + consumers) in room"""
        room = self._get_room(workspace_id, room_id)
        if not room:
            return

        message_text = json.dumps(message)
        participants = []

        # Add producer if exists
        if room.producer:
            participants.append(room.producer)

        # Add all consumers
        participants.extend(room.consumers)

        failed = []
        sent_count = 0

        for participant_id in participants:
            if participant_id in self.connections:
                try:
                    await self.connections[participant_id].send_text(message_text)
                    sent_count += 1
                except Exception:
                    logger.exception(f"Error sending message to {participant_id}")
                    failed.append(participant_id)

        # Cleanup failed connections
        for participant_id in failed:
            metadata = self.connection_metadata.get(participant_id)
            if metadata:
                self.leave_room(
                    metadata["workspace_id"], metadata["room_id"], participant_id
                )
            if participant_id in self.connections:
                del self.connections[participant_id]
            if participant_id in self.connection_metadata:
                del self.connection_metadata[participant_id]

        logger.debug(
            f"Broadcast message to {sent_count}/{len(participants)} participants in room {room_id}"
        )

    async def _send_to_participant(self, participant_id: str, message: dict):
        """Send message to specific participant"""
        if participant_id in self.connections:
            try:
                await self.connections[participant_id].send_text(json.dumps(message))
            except Exception:
                logger.exception(f"Error sending message to {participant_id}")
                if participant_id in self.connections:
                    del self.connections[participant_id]

    # ============= CONNECTION MONITORING =============

    def get_connection_stats(self) -> dict:
        """Get connection statistics and metadata"""
        stats = {
            "total_connections": len(self.connections),
            "total_workspaces": len(self.workspaces),
            "total_rooms": sum(len(rooms) for rooms in self.workspaces.values()),
            "connections_by_role": {"producer": 0, "consumer": 0},
            "connections_by_workspace": {},
            "active_connections": [],
        }

        # Count by role and collect active connections
        for participant_id, metadata in self.connection_metadata.items():
            role = metadata["role"]
            workspace_id = metadata["workspace_id"]
            room_id = metadata["room_id"]

            stats["connections_by_role"][role.value] += 1

            if workspace_id not in stats["connections_by_workspace"]:
                stats["connections_by_workspace"][workspace_id] = {
                    "producer": 0,
                    "consumer": 0,
                    "rooms": 0,
                }
            stats["connections_by_workspace"][workspace_id][role.value] += 1

            # Count unique rooms per workspace
            if workspace_id in self.workspaces:
                stats["connections_by_workspace"][workspace_id]["rooms"] = len(
                    self.workspaces[workspace_id]
                )

            stats["active_connections"].append({
                "participant_id": participant_id,
                "workspace_id": workspace_id,
                "room_id": room_id,
                "role": role.value,
                "connected_at": metadata["connected_at"].isoformat(),
                "last_activity": metadata["last_activity"].isoformat(),
                "message_count": metadata["message_count"],
            })

        return stats

    # ============= EXTERNAL API METHODS =============

    async def send_command_to_room(
        self, workspace_id: str, room_id: str, joints: list[dict]
    ):
        changed_joints = self.update_joints(workspace_id, room_id, joints)

        if changed_joints:
            await self._broadcast_to_consumers(
                workspace_id,
                room_id,
                {
                    "type": MessageType.JOINT_UPDATE.value,
                    "data": changed_joints,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "source": "api",
                },
            )

        return len(changed_joints)

    # ============= CLEANUP MANAGEMENT =============

    async def manual_cleanup(self) -> dict:
        """Manually trigger room cleanup and return results"""
        logger.info("Manual robotics room cleanup triggered")
        rooms_before = sum(len(rooms) for rooms in self.workspaces.values())
        await self._cleanup_inactive_rooms()
        rooms_after = sum(len(rooms) for rooms in self.workspaces.values())

        return {
            "cleanup_triggered": True,
            "rooms_before": rooms_before,
            "rooms_after": rooms_after,
            "rooms_removed": rooms_before - rooms_after,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

    def get_cleanup_status(self) -> dict:
        """Get cleanup system status and configuration"""
        current_time = datetime.now(tz=UTC)

        # Calculate room ages and activity
        room_info = []
        for workspace_id, rooms in self.workspaces.items():
            for room_id, room in rooms.items():
                # Find latest activity for this room
                latest_activity = room.last_activity
                for metadata in self.connection_metadata.values():
                    if (
                        metadata["workspace_id"] == workspace_id
                        and metadata["room_id"] == room_id
                    ):
                        latest_activity = max(
                            latest_activity, metadata["last_activity"]
                        )

                age = current_time - room.created_at
                inactivity = current_time - latest_activity

                room_info.append({
                    "workspace_id": workspace_id,
                    "room_id": room_id,
                    "age_minutes": age.total_seconds() / 60,
                    "inactivity_minutes": inactivity.total_seconds() / 60,
                    "has_connections": any(
                        metadata["workspace_id"] == workspace_id
                        and metadata["room_id"] == room_id
                        for metadata in self.connection_metadata.values()
                    ),
                    "will_be_cleaned": inactivity > self.inactivity_timeout,
                })

        return {
            "service": "robotics",
            "cleanup_enabled": self._cleanup_task is not None,
            "inactivity_timeout_minutes": self.inactivity_timeout.total_seconds() / 60,
            "cleanup_interval_minutes": self.cleanup_interval.total_seconds() / 60,
            "total_rooms": len(room_info),
            "rooms": room_info,
            "timestamp": current_time.isoformat(),
        }
