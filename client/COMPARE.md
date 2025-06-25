# Client Library API Comparison

This table shows the correspondence between the Python and JavaScript/TypeScript client libraries for RobotHub TransportServer.

## 📦 Installation

| Python | JavaScript/TypeScript |
|--------|----------------------|
| `uv add transport-server-client` | `bun add @robothub/transport-server-client` |

## 🔧 Imports

| Python | JavaScript/TypeScript |
|--------|----------------------|
| `from transport_server_client import RoboticsProducer` | `import { robotics } from '@robothub/transport-server-client'` |
| `from transport_server_client import RoboticsConsumer` | `const producer = new robotics.RoboticsProducer()` |
| `from transport_server_client.video import VideoProducer` | `import { video } from '@robothub/transport-server-client'` |
| `from transport_server_client.video import VideoConsumer` | `const producer = new video.VideoProducer()` |

## 🤖 Robotics Producer

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Create instance** | `producer = RoboticsProducer('http://localhost:8000')` | `const producer = new robotics.RoboticsProducer('http://localhost:8000')` |
| **Connect to room** | `await producer.connect(workspace_id, room_id)` | `await producer.connect(workspaceId, roomId)` |
| **Create room** | `room_info = await producer.create_room()` | `const { workspaceId, roomId } = await producer.createRoom()` |
| **Send joint update** | `await producer.send_joint_update(joints)` | `await producer.sendJointUpdate(joints)` |
| **Send state sync** | `await producer.send_state_sync(state)` | `await producer.sendStateSync(state)` |
| **Emergency stop** | `await producer.send_emergency_stop(reason)` | `await producer.sendEmergencyStop(reason)` |
| **List rooms** | `rooms = await producer.list_rooms(workspace_id)` | `const rooms = await producer.listRooms(workspaceId)` |
| **Delete room** | `await producer.delete_room(workspace_id, room_id)` | `await producer.deleteRoom(workspaceId, roomId)` |
| **Disconnect** | `await producer.disconnect()` | `await producer.disconnect()` |

## 🤖 Robotics Consumer

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Create instance** | `consumer = RoboticsConsumer('http://localhost:8000')` | `const consumer = new robotics.RoboticsConsumer('http://localhost:8000')` |
| **Connect to room** | `await consumer.connect(workspace_id, room_id)` | `await consumer.connect(workspaceId, roomId)` |
| **Get current state** | `state = await consumer.get_state_sync()` | `const state = await consumer.getStateSyncAsync()` |
| **Joint update callback** | `consumer.on_joint_update(callback)` | `consumer.onJointUpdate(callback)` |
| **State sync callback** | `consumer.on_state_sync(callback)` | `consumer.onStateSync(callback)` |
| **Error callback** | `consumer.on_error(callback)` | `consumer.onError(callback)` |
| **Connected callback** | `consumer.on_connected(callback)` | `consumer.onConnected(callback)` |
| **Disconnected callback** | `consumer.on_disconnected(callback)` | `consumer.onDisconnected(callback)` |
| **Disconnect** | `await consumer.disconnect()` | `await consumer.disconnect()` |

## 📹 Video Producer

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Create instance** | `producer = VideoProducer('http://localhost:8000')` | `const producer = new video.VideoProducer('http://localhost:8000')` |
| **Connect to room** | `await producer.connect(workspace_id, room_id)` | `await producer.connect(workspaceId, roomId)` |
| **Start camera** | `await producer.start_camera(config)` | `await producer.startCamera(constraints)` |
| **Start screen share** | `await producer.start_screen_share()` | `await producer.startScreenShare()` |
| **Stop streaming** | `await producer.stop_streaming()` | `await producer.stopStreaming()` |
| **Update config** | `await producer.update_video_config(config)` | `await producer.updateVideoConfig(config)` |
| **Disconnect** | `await producer.disconnect()` | `await producer.disconnect()` |

## 📹 Video Consumer

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Create instance** | `consumer = VideoConsumer('http://localhost:8000')` | `const consumer = new video.VideoConsumer('http://localhost:8000')` |
| **Connect to room** | `await consumer.connect(workspace_id, room_id)` | `await consumer.connect(workspaceId, roomId)` |
| **Start receiving** | `await consumer.start_receiving()` | `await consumer.startReceiving()` |
| **Stop receiving** | `await consumer.stop_receiving()` | `await consumer.stopReceiving()` |
| **Attach to video element** | N/A (Python) | `consumer.attachToVideoElement(videoElement)` |
| **Frame callback** | `consumer.on_frame_update(callback)` | `consumer.onFrameUpdate(callback)` |
| **Stream started callback** | `consumer.on_stream_started(callback)` | `consumer.onStreamStarted(callback)` |
| **Stream stopped callback** | `consumer.on_stream_stopped(callback)` | `consumer.onStreamStopped(callback)` |
| **Disconnect** | `await consumer.disconnect()` | `await consumer.disconnect()` |

## ⚡ Factory Functions

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Quick producer** | `producer = await create_producer_client(url)` | `const producer = await robotics.createProducerClient(url)` |
| **Quick consumer** | `consumer = await create_consumer_client(room_id, url)` | `const consumer = await robotics.createConsumerClient(workspaceId, roomId, url)` |

## 🔧 Context Managers / Lifecycle

| Operation | Python | JavaScript/TypeScript |
|-----------|--------|----------------------|
| **Auto cleanup** | `async with RoboticsProducer(url) as producer:` | No built-in equivalent |
| **Check connection** | `producer.is_connected()` | `producer.isConnected()` |
| **Connection info** | `info = producer.get_connection_info()` | `const info = producer.getConnectionInfo()` |

## 📝 Data Formats

### Joint Data

| Python | JavaScript/TypeScript |
|--------|----------------------|
| `{'name': 'shoulder', 'value': 45.0}` | `{ name: 'shoulder', value: 45.0 }` |
| `[{'name': 'shoulder', 'value': 45.0}]` | `[{ name: 'shoulder', value: 45.0 }]` |

### State Data

| Python | JavaScript/TypeScript |
|--------|----------------------|
| `{'shoulder': 45.0, 'elbow': -30.0}` | `{ shoulder: 45.0, elbow: -30.0 }` |

### Room Info Response

| Python | JavaScript/TypeScript |
|--------|----------------------|
| `{'workspace_id': 'uuid', 'room_id': 'uuid'}` | `{ workspaceId: 'uuid', roomId: 'uuid' }` |

## 🔄 Naming Conventions

| Python (snake_case) | JavaScript/TypeScript (camelCase) |
|---------------------|-----------------------------------|
| `send_joint_update` | `sendJointUpdate` |
| `send_state_sync` | `sendStateSync` |
| `get_state_sync` | `getStateSyncAsync` |
| `on_joint_update` | `onJointUpdate` |
| `create_room` | `createRoom` |
| `list_rooms` | `listRooms` |
| `workspace_id` | `workspaceId` |
| `room_id` | `roomId` |
| `start_camera` | `startCamera` |
| `stop_streaming` | `stopStreaming` |

---

**Both libraries provide the same functionality with language-appropriate conventions!** 🤖✨ 