# RobotHub TransportServer Python Client

A Python client library for real-time robotics control and video streaming via the RobotHub TransportServer platform. Built with AsyncIO for high-performance concurrent operations.

## 🎯 Purpose

This client library provides **easy access** to the RobotHub TransportServer from Python applications:

- **Robotics Control**: Send joint commands and receive robot state updates
- **Video Streaming**: Stream and receive video feeds via WebRTC
- **Multi-Workspace**: Organize connections across isolated workspaces
- **AsyncIO Support**: Non-blocking operations for real-time robotics

## 📦 Installation

```bash
uv add transport-server-client
```

Or install from source:
```bash
uv pip install -e .
```

## 🚀 Quick Start

### Robotics Control

#### Producer (Send Commands)

```python
import asyncio
from transport_server_client import RoboticsProducer

async def main():
    producer = RoboticsProducer('http://localhost:8000')
    
    # Create room and connect
    room_id = await producer.create_room()
    await producer.connect(room_id)
    
    # Send joint commands
    await producer.send_joint_update([
        {'name': 'shoulder', 'value': 45.0},
        {'name': 'elbow', 'value': -20.0}
    ])
    
    # Send complete state
    await producer.send_state_sync({
        'shoulder': 60.0,
        'elbow': -30.0,
        'wrist': 15.0
    })
    
    await producer.disconnect()

asyncio.run(main())
```

#### Consumer (Receive Commands)

```python
import asyncio
from transport_server_client import RoboticsConsumer

async def main():
    consumer = RoboticsConsumer('http://localhost:8000')
    await consumer.connect('room-id')
    
    # Handle joint updates
    def on_joint_update(joints):
        print('🤖 Robot moving:', joints)
        # Execute on your robot hardware
    
    def on_state_sync(state):
        print('📊 Robot state:', state)
    
    consumer.on_joint_update(on_joint_update)
    consumer.on_state_sync(on_state_sync)
    
    # Keep running
    await asyncio.sleep(60)
    await consumer.disconnect()

asyncio.run(main())
```

### Video Streaming

```python
import asyncio
from transport_server_client.video import VideoProducer, VideoConsumer

async def video_example():
    # Producer - Stream video
    producer = VideoProducer('http://localhost:8000')
    room_info = await producer.create_room()
    await producer.connect(room_info['workspace_id'], room_info['room_id'])
    await producer.start_camera()
    
    # Consumer - Receive video
    consumer = VideoConsumer('http://localhost:8000')
    await consumer.connect(room_info['workspace_id'], room_info['room_id'])
    
    def on_frame(frame_data):
        print(f'Frame received: {len(frame_data)} bytes')
    
    consumer.on_frame_update(on_frame)
    await consumer.start_receiving()
    
    await asyncio.sleep(30)  # Stream for 30 seconds
    
    await producer.disconnect()
    await consumer.disconnect()

asyncio.run(video_example())
```

## 📚 API Reference

### RoboticsProducer

```python
# Connection
await producer.connect(workspace_id, room_id)
room_info = await producer.create_room()  # Auto-generates IDs
await producer.disconnect()

# Control
await producer.send_joint_update(joints)
await producer.send_state_sync(state)
await producer.send_emergency_stop(reason)

# Room management
rooms = await producer.list_rooms(workspace_id)
await producer.delete_room(workspace_id, room_id)
```

### RoboticsConsumer

```python
# Connection
await consumer.connect(workspace_id, room_id)
state = await consumer.get_state_sync()

# Event callbacks
consumer.on_joint_update(callback)
consumer.on_state_sync(callback)
consumer.on_emergency_stop(callback)
consumer.on_error(callback)
```

### Video APIs

```python
# VideoProducer
await producer.start_camera(config)
await producer.start_screen_share()
await producer.stop_streaming()

# VideoConsumer
await consumer.start_receiving()
consumer.on_frame_update(callback)
consumer.on_stream_started(callback)
```

## ⚡ Factory Functions

Quick setup helpers:

```python
from transport_server_client import create_producer_client, create_consumer_client

# Quick producer setup
producer = await create_producer_client('http://localhost:8000')

# Quick consumer setup  
consumer = await create_consumer_client('room-id', 'http://localhost:8000')
```

## 🔧 Context Managers

Automatic cleanup with context managers:

```python
async with RoboticsProducer('http://localhost:8000') as producer:
    room_id = await producer.create_room()
    await producer.connect(room_id)
    
    await producer.send_state_sync({'joint1': 45.0})
    # Automatically disconnected when exiting
```

## 🛠️ Development

```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
pytest
```

---

**Start controlling robots with Python!** 🤖✨
