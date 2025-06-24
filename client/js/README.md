# RobotHub TransportServer JavaScript/TypeScript Client

A TypeScript/JavaScript client library for real-time robotics control and video streaming via the RobotHub TransportServer platform. Supports both browser and Node.js environments.

## 🎯 Purpose

This client library provides **easy access** to the RobotHub TransportServer from JavaScript/TypeScript applications:

- **Robotics Control**: Send joint commands and receive robot state updates
- **Video Streaming**: Stream and receive video feeds via WebRTC
- **Multi-Workspace**: Organize connections across isolated workspaces
- **Real-time Communication**: WebSocket-based bidirectional messaging

## 📦 Installation

```bash
bun add @robothub/transport-server-client
```

## 🚀 Quick Start

### Robotics Control

```typescript
import { robotics } from '@robothub/transport-server-client';

// Producer - Send commands to robot
const producer = new robotics.RoboticsProducer('http://localhost:8000');
await producer.connect(workspaceId, roomId);

await producer.sendJointUpdate([
  { name: 'shoulder', value: 45.0 },
  { name: 'elbow', value: -30.0 }
]);

// Consumer - Receive robot state
const consumer = new robotics.RoboticsConsumer('http://localhost:8000');
await consumer.connect(workspaceId, roomId);

consumer.onJointUpdate((joints) => {
  console.log('Robot moving:', joints);
});
```

### Video Streaming

```typescript
import { video } from '@robothub/transport-server-client';

// Producer - Stream video
const videoProducer = new video.VideoProducer('http://localhost:8000');
await videoProducer.connect(workspaceId, roomId);
await videoProducer.startCamera();

// Consumer - Receive video
const videoConsumer = new video.VideoConsumer('http://localhost:8000');
await videoConsumer.connect(workspaceId, roomId);

const videoElement = document.getElementById('video');
videoConsumer.attachToVideoElement(videoElement);
```

## 📚 API Reference

### Robotics Producer

```typescript
// Connection
await producer.connect(workspaceId, roomId)
await producer.createRoom() // Auto-generates IDs
await producer.disconnect()

// Control
await producer.sendJointUpdate(joints)
await producer.sendStateSync(state)
await producer.sendEmergencyStop(reason)
```

### Robotics Consumer

```typescript
// Connection
await consumer.connect(workspaceId, roomId)

// Events
consumer.onJointUpdate(callback)
consumer.onStateSync(callback)
consumer.onError(callback)

// State
const state = await consumer.getStateSyncAsync()
```

### Video Producer

```typescript
// Streaming
await producer.startCamera(constraints)
await producer.startScreenShare()
await producer.stopStreaming()
await producer.updateVideoConfig(config)
```

### Video Consumer

```typescript
// Receiving
await consumer.startReceiving()
consumer.attachToVideoElement(videoElement)

// Events
consumer.onStreamStarted(callback)
consumer.onStreamStopped(callback)
```

## 🔧 Room Management

```typescript
// Create rooms and workspaces
const { workspaceId, roomId } = await producer.createRoom();

// List and manage rooms
const rooms = await producer.listRooms(workspaceId);
const roomInfo = await producer.getRoomInfo(workspaceId, roomId);
const success = await producer.deleteRoom(workspaceId, roomId);
```

## ⚡ Factory Functions

Quick setup helpers:

```typescript
// Quick producer setup
const producer = await robotics.createProducerClient('http://localhost:8000');

// Quick consumer setup
const consumer = await robotics.createConsumerClient(workspaceId, roomId, 'http://localhost:8000');
```

## 🛠️ Development

```bash
# Install dependencies
bun install

# Build library
bun run build

# Type checking
bun run typecheck
```

---

**Start controlling robots with JavaScript!** 🤖✨
