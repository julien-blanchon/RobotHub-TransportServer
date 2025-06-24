# LeRobot Arena JavaScript/TypeScript Client

A modern TypeScript/JavaScript client library for LeRobot Arena robotics system, providing real-time communication for robot control and monitoring.

## Features

- 🤖 **Producer/Consumer Pattern**: Control robots as producer, monitor as consumer
- 🔄 **Real-time Communication**: WebSocket-based bidirectional communication
- 📡 **REST API Support**: Complete CRUD operations for rooms and state
- 🎯 **Type Safety**: Full TypeScript support with comprehensive type definitions
- 🚨 **Safety Features**: Emergency stop functionality built-in
- 🔧 **Modular Design**: Import only what you need
- 🧪 **Well Tested**: Comprehensive test suite with Bun test

## Installation

```bash
# Install the package (when published)
npm install lerobot-arena-client

# Or for local development
git clone <repository>
cd client/js
bun install
bun run build
```

## Quick Start

### Producer (Robot Controller)

```typescript
import { RoboticsProducer, createProducerClient } from '@robothub/transport-server-client';

// Method 1: Manual setup
const producer = new RoboticsProducer('http://localhost:8000');
const roomId = await producer.createRoom();
await producer.connect(roomId);

// Method 2: Factory function (recommended)
const producer = await createProducerClient('http://localhost:8000');

// Send robot commands
await producer.sendJointUpdate([
  { name: 'shoulder', value: 45.0 },
  { name: 'elbow', value: -30.0 }
]);

// Send complete state
await producer.sendStateSync({
  base: 0.0,
  shoulder: 45.0,
  elbow: -30.0,
  wrist: 0.0
});

// Emergency stop
await producer.sendEmergencyStop('Safety stop triggered');
```

### Consumer (Robot Monitor)

```typescript
import { RoboticsConsumer, createConsumerClient } from '@robothub/transport-server-client';

// Connect to existing room
const consumer = await createConsumerClient(roomId, 'http://localhost:8000');

// Set up event listeners
consumer.onJointUpdate((joints) => {
  console.log('Joints updated:', joints);
});

consumer.onStateSync((state) => {
  console.log('State synced:', state);
});

consumer.onError((error) => {
  console.error('Error:', error);
});

// Get current state
const currentState = await consumer.getStateSyncAsync();
```

## API Reference

### Core Classes

#### `RoboticsClientCore`
Base class providing common functionality:

```typescript
// REST API methods
await client.listRooms();
await client.createRoom(roomId?);
await client.deleteRoom(roomId);
await client.getRoomInfo(roomId);
await client.getRoomState(roomId);

// Connection management
await client.connectToRoom(roomId, role, participantId?);
await client.disconnect();
client.isConnected();
client.getConnectionInfo();

// Utility
await client.sendHeartbeat();
```

#### `RoboticsProducer`
Producer-specific functionality:

```typescript
const producer = new RoboticsProducer('http://localhost:8000');

// Connection
await producer.connect(roomId, participantId?);

// Commands
await producer.sendJointUpdate(joints);
await producer.sendStateSync(state);
await producer.sendEmergencyStop(reason?);

// Static factory
const producer = await RoboticsProducer.createAndConnect(baseUrl, roomId?, participantId?);
```

#### `RoboticsConsumer`
Consumer-specific functionality:

```typescript
const consumer = new RoboticsConsumer('http://localhost:8000');

// Connection
await consumer.connect(roomId, participantId?);

// Data access
await consumer.getStateSyncAsync();

// Event callbacks
consumer.onJointUpdate(callback);
consumer.onStateSync(callback);
consumer.onError(callback);
consumer.onConnected(callback);
consumer.onDisconnected(callback);

// Static factory
const consumer = await RoboticsConsumer.createAndConnect(roomId, baseUrl, participantId?);
```

### Factory Functions

```typescript
import { createClient, createProducerClient, createConsumerClient } from '@robothub/transport-server-client';

// Generic factory
const client = createClient('producer', 'http://localhost:8000');

// Specialized factories (auto-connect)
const producer = await createProducerClient('http://localhost:8000', roomId?, participantId?);
const consumer = await createConsumerClient(roomId, 'http://localhost:8000', participantId?);
```

### Type Definitions

```typescript
interface JointData {
  name: string;
  value: number;
  speed?: number;
}

interface RoomInfo {
  id: string;
  participants: {
    producer: string | null;
    consumers: string[];
    total: number;
  };
  joints_count: number;
  has_producer?: boolean;
  active_consumers?: number;
}

interface RoomState {
  room_id: string;
  joints: Record<string, number>;
  participants: {
    producer: string | null;
    consumers: string[];
    total: number;
  };
  timestamp: string;
}

type ParticipantRole = 'producer' | 'consumer';
type MessageType = 'joint_update' | 'state_sync' | 'heartbeat' | 'emergency_stop' | 'joined' | 'error';
```

## Examples

The `examples/` directory contains complete working examples:

### Running Examples

```bash
# Build the library first
bun run build

# Run producer example
node examples/basic-producer.js

# Run consumer example (in another terminal)
node examples/basic-consumer.js
```

### Example Files

- **`basic-producer.js`**: Complete producer workflow
- **`basic-consumer.js`**: Interactive consumer example
- **`room-management.js`**: REST API operations
- **`producer-consumer-demo.js`**: Full integration demo

## Development

### Prerequisites

- [Bun](https://bun.sh/) >= 1.0.0
- LeRobot Arena server running on `http://localhost:8000`

### Setup

```bash
# Clone and install
git clone <repository>
cd client/js
bun install

# Development build (watch mode)
bun run dev

# Production build
bun run build

# Run tests
bun test

# Type checking
bun run typecheck

# Linting
bun run lint
bun run lint:fix
```

### Testing

The library includes comprehensive tests:

```bash
# Run all tests
bun test

# Run specific test files
bun test tests/producer.test.ts
bun test tests/consumer.test.ts
bun test tests/integration.test.ts
bun test tests/rest-api.test.ts

# Run tests with coverage
bun test --coverage
```

### Project Structure

```
client/js/
├── src/
│   ├── index.ts              # Main entry point
│   ├── robotics/
│   │   ├── index.ts          # Robotics module exports
│   │   ├── types.ts          # TypeScript type definitions
│   │   ├── core.ts           # Base client class
│   │   ├── producer.ts       # Producer client
│   │   ├── consumer.ts       # Consumer client
│   │   └── factory.ts        # Factory functions
│   ├── video/               # Video module (placeholder)
│   └── audio/               # Audio module (placeholder)
├── tests/
│   ├── producer.test.ts      # Producer tests
│   ├── consumer.test.ts      # Consumer tests
│   ├── integration.test.ts   # Integration tests
│   └── rest-api.test.ts      # REST API tests
├── examples/
│   ├── basic-producer.js     # Producer example
│   ├── basic-consumer.js     # Consumer example
│   └── README.md            # Examples documentation
├── dist/                    # Built output
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Error Handling

The client provides comprehensive error handling:

```typescript
// Connection errors
try {
  await producer.connect(roomId);
} catch (error) {
  console.error('Connection failed:', error.message);
}

// Operation errors
producer.onError((error) => {
  console.error('Producer error:', error);
});

// Network timeouts
const options = { timeout: 10000 }; // 10 seconds
const client = new RoboticsProducer('http://localhost:8000', options);
```

## Configuration

### Client Options

```typescript
interface ClientOptions {
  timeout?: number;           // Request timeout (default: 5000ms)
  reconnect_attempts?: number; // Auto-reconnect attempts (default: 3)
  heartbeat_interval?: number; // Heartbeat interval (default: 30000ms)
}

const producer = new RoboticsProducer('http://localhost:8000', {
  timeout: 10000,
  reconnect_attempts: 5,
  heartbeat_interval: 15000
});
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure the server is running on `http://localhost:8000`
2. **Import Errors**: Make sure you've built the library (`bun run build`)
3. **Room Not Found**: Check that the room ID exists
4. **Permission Denied**: Only one producer per room is allowed
5. **WebSocket Errors**: Check firewall settings and network connectivity

### Debug Mode

Enable detailed logging:

```typescript
// Set up detailed error handling
producer.onError((error) => {
  console.error('Detailed error:', error);
});

// Monitor connection events
producer.onConnected(() => console.log('Connected'));
producer.onDisconnected(() => console.log('Disconnected'));
```

### Performance Tips

- Use the factory functions for simpler setup
- Batch joint updates when possible
- Monitor connection state before sending commands
- Implement proper cleanup in your applications

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `bun test`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

- 📚 [Documentation](./examples/README.md)
- 🐛 [Issue Tracker](https://github.com/lerobot-arena/lerobot-arena/issues)
- 💬 [Discussions](https://github.com/lerobot-arena/lerobot-arena/discussions)
