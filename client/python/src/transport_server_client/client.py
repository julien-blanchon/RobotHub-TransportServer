import asyncio
import json
import logging
from collections.abc import Callable
from urllib.parse import urlparse

import aiohttp
import websockets

logger = logging.getLogger(__name__)


class RoboticsClientCore:
    """Base client for LeRobot Arena robotics API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/robotics"

        # WebSocket connection
        self.websocket: websockets.WebSocketServerProtocol | None = None
        self.workspace_id: str | None = None
        self.room_id: str | None = None
        self.role: str | None = None
        self.participant_id: str | None = None
        self.connected = False

        # Background task for message handling
        self._message_task: asyncio.Task | None = None

    # ============= REST API METHODS =============

    async def list_rooms(self, workspace_id: str) -> list[dict]:
        """List all available rooms in a workspace"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/workspaces/{workspace_id}/rooms"
            ) as response:
                response.raise_for_status()
                result = await response.json()
                # Extract the rooms list from the response
                return result.get("rooms", [])

    async def create_room(
        self, workspace_id: str | None = None, room_id: str | None = None
    ) -> tuple[str, str]:
        """Create a new room and return (workspace_id, room_id)"""
        # Generate workspace ID if not provided
        final_workspace_id = workspace_id or self._generate_workspace_id()

        payload = {}
        if room_id:
            payload["room_id"] = room_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/workspaces/{final_workspace_id}/rooms", json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["workspace_id"], result["room_id"]

    async def delete_room(self, workspace_id: str, room_id: str) -> bool:
        """Delete a room"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.api_base}/workspaces/{workspace_id}/rooms/{room_id}"
            ) as response:
                if response.status == 404:
                    return False
                response.raise_for_status()
                result = await response.json()
                return result["success"]

    async def get_room_state(self, workspace_id: str, room_id: str) -> dict:
        """Get current room state"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/workspaces/{workspace_id}/rooms/{room_id}/state"
            ) as response:
                response.raise_for_status()
                result = await response.json()
                # Extract the state from the response
                return result.get("state", {})

    async def get_room_info(self, workspace_id: str, room_id: str) -> dict:
        """Get basic room information"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/workspaces/{workspace_id}/rooms/{room_id}"
            ) as response:
                response.raise_for_status()
                result = await response.json()
                # Extract the room data from the response
                return result.get("room", {})

    # ============= WEBSOCKET CONNECTION =============

    async def connect_to_room(
        self,
        workspace_id: str,
        room_id: str,
        role: str,
        participant_id: str | None = None,
    ) -> bool:
        """Connect to a room as producer or consumer"""
        if self.connected:
            await self.disconnect()

        self.workspace_id = workspace_id
        self.room_id = room_id
        self.role = role
        self.participant_id = participant_id or f"{role}_{id(self)}"

        # Convert HTTP URL to WebSocket URL
        parsed = urlparse(self.base_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{parsed.netloc}/robotics/workspaces/{workspace_id}/rooms/{room_id}/ws"

        initial_state_sync = None

        try:
            self.websocket = await websockets.connect(ws_url)

            # Send join message
            join_message = {"participant_id": self.participant_id, "role": role}
            await self.websocket.send(json.dumps(join_message))

            # Wait for server response to join message
            try:
                response_text = await asyncio.wait_for(
                    self.websocket.recv(), timeout=5.0
                )
                response = json.loads(response_text)

                if response.get("type") == "error":
                    logger.error(
                        f"Server rejected connection: {response.get('message')}"
                    )
                    await self.websocket.close()
                    return False
                if response.get("type") == "state_sync":
                    # Consumer receives initial state sync, store it and wait for joined message
                    logger.debug("Received initial state sync")
                    initial_state_sync = response
                    # Wait for the joined message
                    response_text = await asyncio.wait_for(
                        self.websocket.recv(), timeout=5.0
                    )
                    response = json.loads(response_text)
                    if response.get("type") == "joined":
                        logger.info(f"Successfully joined room {room_id} as {role}")
                    elif response.get("type") == "error":
                        logger.error(
                            f"Server rejected connection: {response.get('message')}"
                        )
                        await self.websocket.close()
                        return False
                    else:
                        logger.warning(f"Unexpected response from server: {response}")
                elif response.get("type") == "joined":
                    logger.info(f"Successfully joined room {room_id} as {role}")
                    # Connection successful, continue with setup
                else:
                    logger.warning(f"Unexpected response from server: {response}")

            except TimeoutError:
                logger.error("Timeout waiting for server response")
                await self.websocket.close()
                return False
            except json.JSONDecodeError:
                logger.error("Invalid JSON response from server")
                await self.websocket.close()
                return False

            # Start message handling task
            self._message_task = asyncio.create_task(self._handle_messages())

            self.connected = True
            logger.info(f"Connected to room {room_id} as {role}")

            await self._on_connected()

            # Process initial state sync if we received one
            if initial_state_sync:
                await self._process_message(initial_state_sync)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to room {room_id}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from current room"""
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.connected = False
        self.workspace_id = None
        self.room_id = None
        self.role = None
        self.participant_id = None

        await self._on_disconnected()

        logger.info("Disconnected from room")

    # ============= MESSAGE HANDLING =============

    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.connected = False
            await self._on_disconnected()

    async def _process_message(self, data: dict):
        """Process incoming message based on type - to be overridden by subclasses"""
        msg_type = data.get("type")

        if msg_type == "joined":
            logger.info(
                f"Successfully joined room {data.get('room_id')} as {data.get('role')}"
            )
        elif msg_type == "heartbeat_ack":
            logger.debug("Heartbeat acknowledged")
        else:
            # Let subclasses handle specific message types
            await self._handle_role_specific_message(data)

    async def _handle_role_specific_message(self, data: dict):
        """Handle role-specific messages - to be overridden by subclasses"""

    # ============= UTILITY METHODS =============

    async def send_heartbeat(self):
        """Send heartbeat to server"""
        if not self.connected:
            return

        message = {"type": "heartbeat"}
        await self.websocket.send(json.dumps(message))

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected

    def get_connection_info(self) -> dict:
        """Get current connection information"""
        return {
            "connected": self.connected,
            "workspace_id": self.workspace_id,
            "room_id": self.room_id,
            "role": self.role,
            "participant_id": self.participant_id,
            "base_url": self.base_url,
        }

    # ============= HOOKS FOR SUBCLASSES =============

    async def _on_connected(self):
        """Called when connection is established - to be overridden by subclasses"""

    async def _on_disconnected(self):
        """Called when connection is lost - to be overridden by subclasses"""

    # ============= CONTEXT MANAGER SUPPORT =============

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # ============= WORKSPACE HELPERS =============

    def _generate_workspace_id(self) -> str:
        """Generate a UUID-like workspace ID"""
        import uuid

        return str(uuid.uuid4())


class RoboticsProducer(RoboticsClientCore):
    """Producer client for controlling robots"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self._on_error_callback: Callable[[str], None] | None = None
        self._on_connected_callback: Callable[[], None] | None = None
        self._on_disconnected_callback: Callable[[], None] | None = None

    async def connect(
        self, workspace_id: str, room_id: str, participant_id: str | None = None
    ) -> bool:
        """Connect as producer to a room"""
        return await self.connect_to_room(
            workspace_id, room_id, "producer", participant_id
        )

    # ============= PRODUCER METHODS =============

    async def send_joint_update(self, joints: list[dict]):
        """Send joint updates"""
        if not self.connected:
            raise ValueError("Must be connected to send joint updates")

        message = {"type": "joint_update", "data": joints}
        await self.websocket.send(json.dumps(message))

    async def send_state_sync(self, state: dict):
        """Send state synchronization (convert dict to list format)"""
        joints = [{"name": name, "value": value} for name, value in state.items()]
        await self.send_joint_update(joints)

    async def send_emergency_stop(self, reason: str = "Emergency stop"):
        """Send emergency stop signal"""
        if not self.connected:
            raise ValueError("Must be connected to send emergency stop")

        message = {"type": "emergency_stop", "reason": reason}
        await self.websocket.send(json.dumps(message))

    # ============= EVENT CALLBACKS =============

    def on_error(self, callback: Callable[[str], None]):
        """Set callback for error events"""
        self._on_error_callback = callback

    def on_connected(self, callback: Callable[[], None]):
        """Set callback for connection events"""
        self._on_connected_callback = callback

    def on_disconnected(self, callback: Callable[[], None]):
        """Set callback for disconnection events"""
        self._on_disconnected_callback = callback

    # ============= OVERRIDDEN HOOKS =============

    async def _on_connected(self):
        if self._on_connected_callback:
            self._on_connected_callback()

    async def _on_disconnected(self):
        if self._on_disconnected_callback:
            self._on_disconnected_callback()

    async def _handle_role_specific_message(self, data: dict):
        """Handle producer-specific messages"""
        msg_type = data.get("type")

        if msg_type == "emergency_stop":
            logger.warning(f"🚨 Emergency stop: {data.get('reason', 'Unknown reason')}")
            if self._on_error_callback:
                self._on_error_callback(
                    f"Emergency stop: {data.get('reason', 'Unknown reason')}"
                )

        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Server error: {error_msg}")
            if self._on_error_callback:
                self._on_error_callback(error_msg)

        else:
            logger.warning(f"Unknown message type for producer: {msg_type}")


class RoboticsConsumer(RoboticsClientCore):
    """Consumer client for receiving robot commands"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self._on_state_sync_callback: Callable[[dict], None] | None = None
        self._on_joint_update_callback: Callable[[list], None] | None = None
        self._on_error_callback: Callable[[str], None] | None = None
        self._on_connected_callback: Callable[[], None] | None = None
        self._on_disconnected_callback: Callable[[], None] | None = None

    async def connect(
        self, workspace_id: str, room_id: str, participant_id: str | None = None
    ) -> bool:
        """Connect as consumer to a room"""
        return await self.connect_to_room(
            workspace_id, room_id, "consumer", participant_id
        )

    # ============= CONSUMER METHODS =============

    async def get_state_sync(self) -> dict:
        """Get current state synchronously"""
        if not self.workspace_id or not self.room_id:
            raise ValueError("Must be connected to a room")

        state = await self.get_room_state(self.workspace_id, self.room_id)
        return state.get("joints", {})

    # ============= EVENT CALLBACKS =============

    def on_state_sync(self, callback: Callable[[dict], None]):
        """Set callback for state synchronization events"""
        self._on_state_sync_callback = callback

    def on_joint_update(self, callback: Callable[[list], None]):
        """Set callback for joint update events"""
        self._on_joint_update_callback = callback

    def on_error(self, callback: Callable[[str], None]):
        """Set callback for error events"""
        self._on_error_callback = callback

    def on_connected(self, callback: Callable[[], None]):
        """Set callback for connection events"""
        self._on_connected_callback = callback

    def on_disconnected(self, callback: Callable[[], None]):
        """Set callback for disconnection events"""
        self._on_disconnected_callback = callback

    # ============= OVERRIDDEN HOOKS =============

    async def _on_connected(self):
        if self._on_connected_callback:
            self._on_connected_callback()

    async def _on_disconnected(self):
        if self._on_disconnected_callback:
            self._on_disconnected_callback()

    async def _handle_role_specific_message(self, data: dict):
        """Handle consumer-specific messages"""
        msg_type = data.get("type")

        if msg_type == "state_sync":
            if self._on_state_sync_callback:
                self._on_state_sync_callback(data.get("data", {}))

        elif msg_type == "joint_update":
            if self._on_joint_update_callback:
                self._on_joint_update_callback(data.get("data", []))

        elif msg_type == "emergency_stop":
            logger.warning(f"🚨 Emergency stop: {data.get('reason', 'Unknown reason')}")
            if self._on_error_callback:
                self._on_error_callback(
                    f"Emergency stop: {data.get('reason', 'Unknown reason')}"
                )

        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Server error: {error_msg}")
            if self._on_error_callback:
                self._on_error_callback(error_msg)

        else:
            logger.warning(f"Unknown message type for consumer: {msg_type}")


# ============= FACTORY FUNCTIONS =============


def create_client(role: str, base_url: str = "http://localhost:8000"):
    """Factory function to create the appropriate client based on role"""
    if role == "producer":
        return RoboticsProducer(base_url)
    if role == "consumer":
        return RoboticsConsumer(base_url)
    raise ValueError(f"Invalid role: {role}. Must be 'producer' or 'consumer'")


async def create_producer_client(
    base_url: str = "http://localhost:8000",
    workspace_id: str | None = None,
    room_id: str | None = None,
) -> RoboticsProducer:
    """Create and connect a producer client"""
    client = RoboticsProducer(base_url)

    workspace_id, room_id = await client.create_room(workspace_id, room_id)
    await client.connect(workspace_id, room_id)
    return client


async def create_consumer_client(
    workspace_id: str, room_id: str, base_url: str = "http://localhost:8000"
) -> RoboticsConsumer:
    """Create and connect a consumer client"""
    client = RoboticsConsumer(base_url)
    await client.connect(workspace_id, room_id)
    return client
