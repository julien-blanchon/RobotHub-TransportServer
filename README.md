---
title: RobotHub TransportServer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
suggested_hardware: cpu-upgrade
suggested_storage: small
short_description: Real-time robotics control and video streaming platform
tags:
  - robotics
  - control
  - websocket
  - fastapi
  - svelte
  - real-time
  - video-streaming
  - transport-server
  - robothub
pinned: true
fullWidth: true
---

# 🤖 RobotHub TransportServer

A high-performance, real-time communication platform for robotics control and video streaming. Built for multi-tenant environments with WebSocket and WebRTC technologies.

## 🚀 Overview

RobotHub TransportServer enables real-time, bidirectional communication between robotics systems, cameras, and control interfaces. It provides a unified platform for:

- **Real-time robot joint control** via WebSocket connections
- **Live video streaming** via WebRTC technology  
- **Multi-workspace isolation** for secure multi-tenant deployments
- **Producer/Consumer architecture** for scalable robotics applications
- **Cross-platform client libraries** (JavaScript/TypeScript and Python)

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    RobotHub TransportServer                 │
├─────────────────────────────────────────────────────────────┤
│  🌐 REST API          │  🔌 WebSocket          │  📹 WebRTC  │
│  - Room management    │  - Real-time control   │  - Video    │
│  - Workspace control  │  - Joint updates       │  - Streaming│
│  - Status & health    │  - State sync          │  - P2P conn │
├─────────────────────────────────────────────────────────────┤
│             Multi-Workspace & Room Management               │
│  workspace_1/          workspace_2/          workspace_n/   │
│  ├── robotics_room_1  ├── robotics_room_1   ├── ...        │
│  ├── robotics_room_2  ├── video_room_1      │              │
│  └── video_room_1     └── video_room_2      │              │
└─────────────────────────────────────────────────────────────┘
```

### Producer/Consumer Pattern

**Robotics Control:**
- **Producer**: Sends joint commands and control signals
- **Consumer**: Receives commands and executes robot movements

**Video Streaming:**
- **Producer**: Streams camera feeds or screen content
- **Consumer**: Receives and displays video streams

## 🛠️ Key Features

### ✅ Real-time Robotics Control
- Joint-level robot control with normalized values
- Emergency stop mechanisms
- State synchronization between multiple clients
- Support for 6-DOF robotic arms (extensible)

### ✅ WebRTC Video Streaming
- Low-latency video streaming
- Multiple camera support
- Screen sharing capabilities
- Automatic quality adaptation

### ✅ Multi-Workspace Architecture
- Complete isolation between workspaces
- UUID-based workspace identification
- Scalable room management within workspaces

### ✅ Cross-Platform Clients
- **JavaScript/TypeScript**: Browser and Node.js support
- **Python**: AsyncIO-based client for robotics applications
- Consistent API across all platforms

### ✅ Production Ready
- Docker containerization
- Health monitoring endpoints
- Comprehensive logging
- Error handling and recovery

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/julien-blanchon/RobotHub-TransportServer
cd RobotHub-TransportServer

# Build and run with Docker
docker build -t robothub-transport-server .
docker run -p 8000:8000 robothub-transport-server
```

### Development Setup

```bash
# Install Python dependencies
cd server
uv venv
source .venv/bin/activate
uv sync
uv pip install -e .

# Start the server
uv run launch_with_ui.py

# The server will be available at:
# - API: http://localhost:8000/api
# - Demo UI: http://localhost:8000
```

## 📚 Client Libraries

### JavaScript/TypeScript

```bash
cd client/js
bun install
bun run build
```

```typescript
import { robotics, video } from '@robothub/transport-server-client';

// Robotics control
const producer = new robotics.RoboticsProducer('http://localhost:8000');
await producer.connect(workspaceId, roomId);
await producer.sendJointUpdate([
  { name: 'joint_1', value: 45.0 },
  { name: 'joint_2', value: -30.0 }
]);

// Video streaming
const videoProducer = new video.VideoProducer('http://localhost:8000');
await videoProducer.connect(workspaceId, roomId);
await videoProducer.startCamera();
```

### Python

```bash
cd client/python
uv venv
source .venv/bin/activate
uv sync
uv pip install -e .
```

```python
import asyncio
from transport_server_client import RoboticsProducer
from transport_server_client.video import VideoProducer

async def main():
    # Robotics control
    producer = RoboticsProducer('http://localhost:8000')
    await producer.connect(workspace_id, room_id)
    await producer.send_joint_update([
        {'name': 'joint_1', 'value': 45.0},
        {'name': 'joint_2', 'value': -30.0}
    ])
    
    # Video streaming
    video_producer = VideoProducer('http://localhost:8000')
    await video_producer.connect(workspace_id, room_id)
    await video_producer.start_camera()

asyncio.run(main())
```

## 🎮 Interactive Demo

The included demo application showcases all features:

```bash
cd demo
bun install
bun run dev
```

Visit `http://localhost:5173` to access:
- **Workspace Management**: Create and manage isolated environments
- **Robotics Control**: Real-time robot arm control interface
- **Video Streaming**: Camera and screen sharing demos
- **Multi-room Support**: Manage multiple concurrent sessions

## 🔧 API Reference

### REST Endpoints

#### Workspaces & Rooms
```
GET    /robotics/workspaces/{workspace_id}/rooms
POST   /robotics/workspaces/{workspace_id}/rooms
DELETE /robotics/workspaces/{workspace_id}/rooms/{room_id}
GET    /robotics/workspaces/{workspace_id}/rooms/{room_id}/state

GET    /video/workspaces/{workspace_id}/rooms
POST   /video/workspaces/{workspace_id}/rooms
DELETE /video/workspaces/{workspace_id}/rooms/{room_id}
```

#### WebSocket Connections
```
WS /robotics/workspaces/{workspace_id}/rooms/{room_id}/ws
WS /video/workspaces/{workspace_id}/rooms/{room_id}/ws
```

### Message Types

#### Robotics Messages
- `joint_update`: Send/receive joint position commands
- `state_sync`: Synchronize complete robot state
- `emergency_stop`: Emergency stop signal
- `heartbeat`: Connection health monitoring

#### Video Messages
- `stream_started`: Video stream initiated
- `stream_stopped`: Video stream ended  
- `webrtc_offer/answer/ice`: WebRTC signaling
- `video_config_update`: Stream configuration changes

## 🔌 Integration Examples

### ML/AI Robotics Pipeline

```python
# Example: AI model controlling robot via TransportServer
import asyncio
from transport_server_client import RoboticsProducer
from transport_server_client.video import VideoConsumer

class AIRobotController:
    def __init__(self, server_url, workspace_id):
        self.robot_producer = RoboticsProducer(server_url)
        self.camera_consumer = VideoConsumer(server_url)
        self.workspace_id = workspace_id
    
    async def start_control_loop(self):
        # Connect to robot control room
        await self.robot_producer.connect(self.workspace_id, 'robot_control')
        
        # Connect to camera feed
        await self.camera_consumer.connect(self.workspace_id, 'camera_feed')
        
        # Set up frame processing
        self.camera_consumer.on_frame_update(self.process_frame)
    
    async def process_frame(self, frame_data):
        # AI inference on camera frame
        joint_commands = await self.ai_model.predict(frame_data)
        
        # Send robot commands
        await self.robot_producer.send_joint_update(joint_commands)
```

### Multi-Robot Coordination

```typescript
// Example: Coordinating multiple robots
import { robotics } from '@robothub/transport-server-client';

class MultiRobotCoordinator {
  private robots: Map<string, robotics.RoboticsProducer> = new Map();
  
  async addRobot(robotId: string, workspaceId: string, roomId: string) {
    const producer = new robotics.RoboticsProducer();
    await producer.connect(workspaceId, roomId);
    this.robots.set(robotId, producer);
  }
  
  async coordinatedMovement(positions: Map<string, JointUpdate[]>) {
    // Send synchronized commands to all robots
    const promises = Array.from(positions.entries()).map(([robotId, joints]) => {
      const producer = this.robots.get(robotId);
      return producer?.sendJointUpdate(joints);
    });
    
    await Promise.all(promises);
  }
}
```

## 📁 Project Structure

```
RobotHub-TransportServer/
├── server/                 # FastAPI backend server
│   ├── src/
│   │   ├── robotics/      # Robotics control logic
│   │   ├── video/         # Video streaming logic
│   │   └── api.py         # Main API routes
│   └── launch_with_ui.py  # Server launcher
├── client/
│   ├── js/                # JavaScript/TypeScript client
│   └── python/            # Python client library
├── demo/                  # SvelteKit demo application
├── Dockerfile             # Container configuration
└── README.md
```

## 🚢 Deployment

### Production Docker Deployment

```bash
# Build production image
docker build -t robothub-transport-server .

# Run with custom configuration
docker run -d \
  --name robothub-transport-server \
  -p 8000:8000 \
  -e LOG_LEVEL=info \
  robothub-transport-server
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/julien-blanchon/RobotHub-TransportServer
cd RobotHub-TransportServer

# Server development
cd server
uv venv && source .venv/bin/activate
uv sync

# Client development
cd client/js
bun install

# Demo development  
cd demo
bun install
```
