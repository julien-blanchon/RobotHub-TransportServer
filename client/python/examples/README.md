# LeRobot Arena Examples

This directory contains example scripts demonstrating various aspects of the LeRobot Arena robotics system.

## Prerequisites

Before running these examples, ensure you have:

1. **Server running**: Start the LeRobot Arena server
   ```bash
   # From the server directory
   uvicorn src.api.main:app --reload
   ```

2. **Dependencies installed**: Install the Python client
   ```bash
   # From client/python directory
   pip install -e .
   ```

## Examples Overview

### 1. `basic_producer.py`
**Basic Producer Usage**

Demonstrates core producer functionality:
- Creating a room
- Connecting as a producer
- Sending joint updates
- Sending state synchronization
- Basic error handling

```bash
python examples/basic_producer.py
```

### 2. `basic_consumer.py`
**Basic Consumer Usage**

Shows how to connect as a consumer and receive data:
- Connecting to an existing room
- Setting up event callbacks
- Receiving joint updates and state sync
- Getting current room state

```bash
python examples/basic_consumer.py
# You'll need to enter a room ID from a running producer
```

### 3. `room_management.py`
**Room Management Operations**

Demonstrates REST API operations:
- Listing all rooms
- Creating rooms (auto-generated and custom IDs)
- Getting room information and state
- Deleting rooms

```bash
python examples/room_management.py
```

### 4. `producer_consumer_demo.py`
**Complete Producer-Consumer Demo**

Comprehensive demonstration featuring:
- Producer and multiple consumers working together
- Realistic robot movement simulation
- Emergency stop functionality
- State synchronization
- Connection management and cleanup

```bash
python examples/producer_consumer_demo.py
```

### 5. `context_manager_example.py`
**Context Managers and Advanced Patterns**

Shows advanced usage patterns:
- Using clients as context managers for automatic cleanup
- Exception handling with proper resource management
- Factory functions for quick client setup
- Managing multiple clients

```bash
python examples/context_manager_example.py
```

## Running Examples

### Quick Start (All-in-One Demo)
For a complete demonstration, run:
```bash
python examples/producer_consumer_demo.py
```

### Step-by-Step Testing
1. **Start with room management**:
   ```bash
   python examples/room_management.py
   ```

2. **Run producer in one terminal**:
   ```bash
   python examples/basic_producer.py
   ```

3. **Run consumer in another terminal**:
   ```bash
   python examples/basic_consumer.py
   # Use the room ID from the producer
   ```

### Advanced Examples
For more sophisticated patterns:
```bash
python examples/context_manager_example.py
```

## Key Concepts Demonstrated

### Producer Capabilities
- **Room Creation**: Creating and managing robotics rooms
- **Joint Control**: Sending individual joint position updates
- **State Synchronization**: Sending complete robot state
- **Emergency Stop**: Triggering safety stops
- **Error Handling**: Managing connection and communication errors

### Consumer Capabilities
- **Real-time Updates**: Receiving joint position updates
- **State Monitoring**: Getting current robot state
- **Event Callbacks**: Responding to various message types
- **Multiple Consumers**: Supporting multiple clients per room

### Connection Management
- **WebSocket Communication**: Real-time bidirectional communication
- **Auto-reconnection**: Handling connection failures
- **Resource Cleanup**: Proper disconnection and cleanup
- **Context Managers**: Automatic resource management

### Error Handling
- **Connection Failures**: Graceful handling of network issues
- **Invalid Operations**: Handling invalid commands or states
- **Emergency Scenarios**: Safety system demonstrations
- **Resource Management**: Proper cleanup in error conditions

## Example Output

When running the examples, you'll see detailed logging output showing:
- Connection status and events
- Data being sent and received
- Error conditions and handling
- Resource cleanup operations

Example log output:
```
INFO:__main__:Created room: abc123-def456-ghi789
INFO:__main__:[Producer] Connected!
INFO:__main__:[visualizer] Joint update #1: 4 joints
INFO:__main__:[logger] Joint update #1: 4 joints
INFO:__main__:🚨 [Producer] Sending emergency stop!
INFO:__main__:[safety-monitor] ERROR: Emergency stop: Demo emergency stop
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure the server is running on `http://localhost:8000`
2. **Import Errors**: Make sure you've installed the client package (`pip install -e .`)
3. **Room Not Found**: Check that the room ID exists (run `room_management.py` to see active rooms)
4. **Permission Denied**: Only one producer per room is allowed

### Debug Mode
Enable debug logging for more detailed output:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

After running these examples, you can:
- Integrate the client into your own robotics applications
- Modify the examples for your specific robot hardware
- Build custom visualizers or control interfaces
- Implement safety monitoring systems
- Create automated testing scenarios 