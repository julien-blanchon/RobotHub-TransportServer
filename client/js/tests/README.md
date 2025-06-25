# RobotHub TransportServer JavaScript Client Tests

## Overview

This directory contains comprehensive tests for the RobotHub TransportServer JavaScript/TypeScript client library, mirroring the Python test structure. The tests are built using [Bun's test framework](https://bun.sh/docs/test/writing) and provide full coverage of both robotics and video functionality.

## Test Structure

The test suite is organized to match the Python client tests:

```
tests/
├── setup.ts              # Test utilities and helpers (equivalent to conftest.py)
├── producer.test.ts       # RoboticsProducer tests
├── consumer.test.ts       # RoboticsConsumer tests  
├── factory.test.ts        # Factory function tests
├── integration.test.ts    # Integration tests
├── rest-api.test.ts       # REST API tests
├── video-client.test.ts   # Video client tests
└── README.md             # This file
```

## Running Tests

### Prerequisites

1. **Server Running**: Ensure the RobotHub TransportServer is running on `http://localhost:8000`
2. **Dependencies**: Install dependencies with `bun install`

### Run All Tests

```bash
# From the js client directory
bun test

# Or using npm script
bun run test
```

### Run Specific Test Files

```bash
# Run only producer tests
bun test tests/producer.test.ts

# Run only integration tests  
bun test tests/integration.test.ts

# Run with verbose output
bun test --verbose
```

## Test Categories

### 1. Robotics Producer Tests (`producer.test.ts`)
- ✅ Basic connection and disconnection
- ✅ Connection info validation
- ✅ Joint updates and state synchronization
- ✅ Emergency stop functionality
- ✅ Event callbacks (connected, disconnected, error)
- ✅ Error handling for disconnected operations
- ✅ Multiple room connections
- ✅ Custom participant IDs
- ✅ Large data handling
- ✅ High-frequency updates

### 2. Robotics Consumer Tests (`consumer.test.ts`)
- ✅ Basic connection and disconnection
- ✅ Connection info validation
- ✅ State synchronization retrieval
- ✅ Event callbacks setup
- ✅ Multiple consumers in same room
- ✅ Receiving state sync and joint updates
- ✅ Emergency stop reception
- ✅ Custom participant IDs
- ✅ Reconnection scenarios
- ✅ State persistence after producer updates

### 3. Factory Function Tests (`factory.test.ts`)
- ✅ Client creation by role
- ✅ Invalid role handling
- ✅ Auto room creation for producers
- ✅ Specific room connection
- ✅ Producer-consumer pair creation
- ✅ Default URL handling
- ✅ Multiple producer management
- ✅ Nonexistent room error handling

### 4. Integration Tests (`integration.test.ts`)
- ✅ Full producer-consumer workflow
- ✅ Multiple consumers receiving same data
- ✅ Emergency stop propagation
- ✅ Producer reconnection scenarios
- ✅ Late-joining consumers
- ✅ Room state persistence
- ✅ High-frequency update handling

### 5. REST API Tests (`rest-api.test.ts`)
- ✅ Room listing (empty and populated)
- ✅ Room creation (auto and custom IDs)
- ✅ Room information retrieval
- ✅ Room state retrieval
- ✅ Room deletion
- ✅ Error handling for nonexistent rooms

### 6. Video Client Tests (`video-client.test.ts`)
- ✅ Type definitions validation
- ✅ Producer and consumer creation
- ✅ Room creation and listing (when server available)
- ✅ Connection validation
- ✅ Factory function existence
- ✅ Mock frame source functionality
- ✅ Configuration type validation

## Test Results Summary

```
✅ 69 tests passed
❌ 0 tests failed
🔍 187 expect() calls
⏱️ Runtime: ~4 seconds
```

## API Correspondence

The JavaScript tests mirror the Python test structure, ensuring API parity:

| Python Test | JavaScript Test | Coverage |
|-------------|-----------------|----------|
| `test_producer.py` | `producer.test.ts` | ✅ Complete |
| `test_consumer.py` | `consumer.test.ts` | ✅ Complete |
| `test_factory_functions.py` | `factory.test.ts` | ✅ Complete |
| `test_integration.py` | `integration.test.ts` | ✅ Complete |
| `test_rest_api.py` | `rest-api.test.ts` | ✅ Complete |
| `test_video_client.py` | `video-client.test.ts` | ✅ Complete |
| `conftest.py` | `setup.ts` | ✅ Complete |

## Test Features

### Async/Await Support
All tests use modern async/await patterns with proper cleanup:

```typescript
test("producer connection", async () => {
    const { workspaceId, roomId } = await producer.createRoom();
    await producer.connect(workspaceId, roomId);
    expect(producer.isConnected()).toBe(true);
    await producer.disconnect();
});
```

### Message Collection
Tests use a `MessageCollector` utility for testing callbacks:

```typescript
const updateCollector = new MessageCollector(1);
consumer.onJointUpdate(updateCollector.collect);
await producer.sendJointUpdate(joints);
const updates = await updateCollector.waitForMessages(2000);
expect(updates.length).toBeGreaterThanOrEqual(1);
```

### Resource Management
Automatic cleanup prevents test interference:

```typescript
afterEach(async () => {
    if (producer.isConnected()) {
        await producer.disconnect();
    }
    await roomManager.cleanup(producer);
});
```

### Error Testing
Comprehensive error scenario coverage:

```typescript
test("send without connection", async () => {
    await expect(producer.sendJointUpdate([]))
        .rejects.toThrow("Must be connected");
});
```

## Debugging Tests

### Enable Debug Logging
```bash
# Run with debug output
DEBUG=* bun test

# Or specific modules
DEBUG=robotics:* bun test
```

### Test Individual Scenarios
```bash
# Test specific functionality
bun test --grep "emergency stop"
bun test --grep "multiple consumers"
```

### Server Connectivity Issues
If tests fail due to server connectivity:

1. Ensure server is running: `curl http://localhost:8000/health`
2. Check server logs for errors
3. Verify WebSocket connections are allowed
4. Try running tests with longer timeouts

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Add proper cleanup in `afterEach` blocks
3. Use `MessageCollector` for callback testing
4. Test both success and error scenarios
5. Update this README with new test descriptions

## Performance Notes

- Tests run in parallel by default
- Average test suite runtime: ~4 seconds
- Individual test timeouts: 10 seconds
- Message collection timeouts: 2-5 seconds

The JavaScript test suite provides comprehensive validation that the TypeScript/JavaScript client maintains full API compatibility with the Python client while leveraging modern JavaScript testing practices. 