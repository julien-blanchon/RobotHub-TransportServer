# LeRobot Arena Python Client

Python client library for the LeRobot Arena robotics API with separate Producer and Consumer classes.

## Installation

```bash
pip install -e .
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Basic Usage

### Producer (Controller) Example

```python
import asyncio
from lerobot_arena_client import RoboticsProducer

async def main():
    # Create producer client
    producer = RoboticsProducer('http://localhost:8000')
    
    # List available rooms
    rooms = await producer.list_rooms()
    print('Available rooms:', rooms)
    
    # Create new room and connect
    room_id = await producer.create_room()
    await producer.connect(room_id)
    
    # Send initial state
    await producer.send_state_sync({
        'shoulder': 45.0,
        'elbow': -20.0
    })
    
    # Send joint updates (only changed values will be forwarded!)
    await producer.send_joint_update([
        {'name': 'shoulder', 'value': 45.0},
        {'name': 'elbow', 'value': -20.0}
    ])
    
    # Handle errors
    producer.on_error(lambda err: print(f'Error: {err}'))
    
    # Disconnect
    await producer.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Consumer (Robot Executor) Example

```python
import asyncio
from lerobot_arena_client import RoboticsConsumer

async def main():
    consumer = RoboticsConsumer('http://localhost:8000')
    
    # Connect to existing room
    room_id = "your-room-id"
    await consumer.connect(room_id)
    
    # Get initial state
    initial_state = await consumer.get_state_sync()
    print('Initial state:', initial_state)
    
    # Set up event handlers
    def on_state_sync(state):
        print('State sync:', state)
    
    def on_joint_update(joints):
        print('Execute joints:', joints)
        # Execute on actual robot hardware
        for joint in joints:
            print(f"Moving {joint['name']} to {joint['value']}")
    
    def on_error(error):
        print(f'Error: {error}')
    
    # Register callbacks
    consumer.on_state_sync(on_state_sync)
    consumer.on_joint_update(on_joint_update)
    consumer.on_error(on_error)
    
    # Keep running
    try:
        await asyncio.sleep(60)  # Run for 60 seconds
    finally:
        await consumer.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Factory Function Usage

```python
import asyncio
from lerobot_arena_client import create_client

async def main():
    # Create clients using factory function
    producer = create_client("producer", "http://localhost:8000")
    consumer = create_client("consumer", "http://localhost:8000")
    
    # Or use convenience functions
    from lerobot_arena_client import create_producer_client, create_consumer_client
    
    # Quick producer setup (auto-creates room and connects)
    producer = await create_producer_client('http://localhost:8000')
    print(f"Producer connected to room: {producer.room_id}")
    
    # Quick consumer setup (connects to existing room)
    consumer = await create_consumer_client(producer.room_id, 'http://localhost:8000')
    
    # Use context managers for automatic cleanup
    async with RoboticsProducer('http://localhost:8000') as producer:
        room_id = await producer.create_room()
        await producer.connect(room_id)
        await producer.send_state_sync({'joint1': 10.0})

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Example: Producer-Consumer Pair

```python
import asyncio
from lerobot_arena_client import RoboticsProducer, RoboticsConsumer

async def run_producer(room_id: str):
    async with RoboticsProducer() as producer:
        await producer.connect(room_id)
        
        # Simulate sending commands
        for i in range(10):
            await producer.send_state_sync({
                'joint1': i * 10.0,
                'joint2': i * -5.0
            })
            await asyncio.sleep(1)

async def run_consumer(room_id: str):
    async with RoboticsConsumer() as consumer:
        await consumer.connect(room_id)
        
        def handle_joint_update(joints):
            print(f"🤖 Executing: {joints}")
            # Your robot control code here
        
        consumer.on_joint_update(handle_joint_update)
        
        # Keep listening
        await asyncio.sleep(15)

async def main():
    # Create room
    producer = RoboticsProducer()
    room_id = await producer.create_room()
    
    # Run producer and consumer concurrently
    await asyncio.gather(
        run_producer(room_id),
        run_consumer(room_id)
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### RoboticsProducer

**Connection Methods:**
- `connect(room_id, participant_id=None)` - Connect as producer to room

**Control Methods:**
- `send_joint_update(joints)` - Send joint updates
- `send_state_sync(state)` - Send state synchronization (dict format)
- `send_emergency_stop(reason)` - Send emergency stop

**Event Callbacks:**
- `on_error(callback)` - Set error callback
- `on_connected(callback)` - Set connection callback  
- `on_disconnected(callback)` - Set disconnection callback

### RoboticsConsumer

**Connection Methods:**
- `connect(room_id, participant_id=None)` - Connect as consumer to room

**State Methods:**
- `get_state_sync()` - Get current state synchronously

**Event Callbacks:**
- `on_state_sync(callback)` - Set state sync callback
- `on_joint_update(callback)` - Set joint update callback
- `on_error(callback)` - Set error callback
- `on_connected(callback)` - Set connection callback
- `on_disconnected(callback)` - Set disconnection callback

### RoboticsClientCore (Base Class)

**REST API Methods:**
- `list_rooms()` - List all available rooms
- `create_room(room_id=None)` - Create a new room
- `delete_room(room_id)` - Delete a room
- `get_room_state(room_id)` - Get current room state
- `get_room_info(room_id)` - Get basic room information

**Utility Methods:**
- `send_heartbeat()` - Send heartbeat to server
- `is_connected()` - Check connection status
- `get_connection_info()` - Get connection details
- `disconnect()` - Disconnect from room

### Factory Functions

- `create_client(role, base_url)` - Create client by role ("producer" or "consumer")
- `create_producer_client(base_url, room_id=None)` - Create connected producer
- `create_consumer_client(room_id, base_url)` - Create connected consumer

## Requirements

- Python 3.12+
- aiohttp>=3.9.0
- websockets>=12.0

## Migration from v1

The old `RoboticsClient` is still available for backward compatibility but is now an alias to `RoboticsClientCore`. For new code, use the specific `RoboticsProducer` or `RoboticsConsumer` classes for better type safety and cleaner APIs.
