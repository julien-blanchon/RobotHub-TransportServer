# Integration Tests for LeRobot Arena Python Client

Comprehensive integration tests for the LeRobot Arena Python client library.

## Prerequisites

1. **Server Running**: Make sure the LeRobot Arena server is running on `http://localhost:8000`
2. **Dependencies**: Install test dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

### Quick Start
```bash
# Run all tests
python run_tests.py

# Or use pytest directly
pytest -v
```

### Specific Test Categories
```bash
# REST API tests only
pytest tests/test_rest_api.py -v

# Producer tests only  
pytest tests/test_producer.py -v

# Consumer tests only
pytest tests/test_consumer.py -v

# Factory function tests only
pytest tests/test_factory_functions.py -v

# End-to-end integration tests only
pytest tests/test_integration.py -v
```

### Advanced Options
```bash
# Run tests with detailed output
pytest -v -s

# Run specific test
pytest tests/test_producer.py::TestRoboticsProducer::test_send_joint_update -v

# Run tests matching pattern
pytest -k "producer" -v

# Stop on first failure
pytest -x
```

## Test Structure

### `test_rest_api.py`
- Room creation and deletion
- Listing rooms
- Getting room state and info
- Error handling for nonexistent rooms

### `test_producer.py`  
- Producer connection and disconnection
- Sending joint updates and state sync
- Emergency stop functionality
- Event callbacks
- Error conditions and validation
- Context manager support
- Multiple room handling

### `test_consumer.py`
- Consumer connection and disconnection  
- Receiving joint updates and state sync
- Event callbacks and message handling
- Multiple consumers per room
- State synchronization
- Error propagation

### `test_factory_functions.py`
- `create_client()` factory function
- `create_producer_client()` convenience function
- `create_consumer_client()` convenience function
- Parameter validation
- Auto room creation
- Error handling

### `test_integration.py`
- End-to-end producer-consumer workflows
- Multiple consumers receiving same messages
- Emergency stop propagation
- Producer reconnection scenarios
- Late-joining consumers
- High-frequency update handling
- Room state persistence

## Test Fixtures

### Core Fixtures
- `producer`: Clean RoboticsProducer instance
- `consumer`: Clean RoboticsConsumer instance  
- `test_room`: Auto-created and cleaned up room
- `connected_producer`: Producer connected to test room
- `connected_consumer`: Consumer connected to test room
- `producer_consumer_pair`: Connected producer and consumer pair

## Test Coverage

The test suite covers:

✅ **REST API Operations**
- ✅ Room CRUD operations
- ✅ State and info retrieval
- ✅ Error handling

✅ **WebSocket Communication**
- ✅ Connection establishment
- ✅ Message sending/receiving
- ✅ Connection cleanup

✅ **Producer Functionality**
- ✅ Joint updates and state sync
- ✅ Emergency stop
- ✅ Heartbeat
- ✅ Event callbacks

✅ **Consumer Functionality**  
- ✅ Message reception
- ✅ State synchronization
- ✅ Event callbacks
- ✅ Multiple consumer support

✅ **Factory Functions**
- ✅ Client creation
- ✅ Auto room creation
- ✅ Parameter validation

✅ **Edge Cases**
- ✅ Network disconnections
- ✅ Invalid parameters
- ✅ Nonexistent rooms
- ✅ Duplicate connections
- ✅ High-frequency updates

✅ **Integration Scenarios**
- ✅ Full producer-consumer workflows
- ✅ Multi-consumer broadcasting
- ✅ Emergency stop propagation
- ✅ Reconnection handling
- ✅ Late consumer joining

## Running Individual Test Categories

Each test file can be run independently:

```bash
# Test basic REST operations
pytest tests/test_rest_api.py

# Test producer functionality
pytest tests/test_producer.py

# Test consumer functionality  
pytest tests/test_consumer.py

# Test factory functions
pytest tests/test_factory_functions.py

# Test end-to-end scenarios
pytest tests/test_integration.py
```

## Debugging Tests

For debugging failed tests:

```bash
# Run with full output
pytest -v -s --tb=long

# Run single test with debugging
pytest tests/test_producer.py::TestRoboticsProducer::test_send_joint_update -v -s

# Use pdb for interactive debugging
pytest --pdb
```

## Expected Test Results

When all tests pass, you should see output like:

```
🧪 Running LeRobot Arena Python Client Integration Tests
============================================================
⚠️  Make sure the server is running on http://localhost:8000

========================= test session starts =========================
collected 45+ items

tests/test_rest_api.py::TestRestAPI::test_list_rooms_empty PASSED
tests/test_rest_api.py::TestRestAPI::test_create_room PASSED
...
tests/test_integration.py::TestIntegration::test_high_frequency_updates PASSED

========================= 45+ passed in X.XXs =========================

✅ All tests passed!
```

## Troubleshooting

### Common Issues

1. **Server Not Running**
   ```
   ConnectionRefusedError: [Errno 61] Connection refused
   ```
   **Solution**: Start the LeRobot Arena server on `http://localhost:8000`

2. **WebSocket Connection Timeout**
   ```
   TimeoutError: WebSocket connection timeout
   ```
   **Solution**: Check server health and network connectivity

3. **Test Timing Issues**
   - Some tests may be sensitive to timing
   - Increase sleep durations in tests if needed
   - Run tests on a faster machine if possible

4. **Port Conflicts**
   - Make sure port 8000 is available
   - Update `TEST_SERVER_URL` in `conftest.py` if using different port

### Getting Help

If tests fail consistently:
1. Check server logs for errors
2. Run individual test files to isolate issues
3. Use verbose output (`-v -s`) to see detailed information
4. Check network connectivity and firewall settings 