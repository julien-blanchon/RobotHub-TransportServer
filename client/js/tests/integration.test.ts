/**
 * Integration tests for producer-consumer interactions - equivalent to Python's test_integration.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { robotics } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager, MessageCollector, sleep } from "./setup";

const { RoboticsProducer, createConsumerClient, createProducerClient } = robotics;

describe("Integration", () => {
    let roomManager: TestRoomManager;

    beforeEach(() => {
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        // Cleanup handled by individual tests
    });

    test("full producer consumer workflow", async () => {
        // Create producer and room
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            // Create consumer and connect to same room
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                // Set up consumer to collect messages
                const stateCollector = new MessageCollector<Record<string, number>>(1);
                const updateCollector = new MessageCollector(4);
                const errorCollector = new MessageCollector<string>(1);

                consumer.onStateSync(stateCollector.collect);
                consumer.onJointUpdate(updateCollector.collect);
                consumer.onError(errorCollector.collect);

                // Wait for connections to stabilize
                await sleep(200);

                // Producer sends initial state
                const initialState = { shoulder: 0.0, elbow: 0.0, wrist: 0.0 };
                await producer.sendStateSync(initialState);
                await sleep(100);

                // Producer sends series of joint updates
                const jointSequences = [
                    [{ name: "shoulder", value: 45.0 }],
                    [{ name: "elbow", value: -30.0 }],
                    [{ name: "wrist", value: 15.0 }],
                    [
                        { name: "shoulder", value: 90.0 },
                        { name: "elbow", value: -60.0 }
                    ]
                ];

                for (const joints of jointSequences) {
                    await producer.sendJointUpdate(joints);
                    await sleep(100);
                }

                // Wait for all messages to be received
                const receivedUpdates = await updateCollector.waitForMessages(3000);

                // Verify consumer received messages
                expect(receivedUpdates.length).toBeGreaterThanOrEqual(4);

                // Verify final state
                const finalState = await consumer.getStateSyncAsync();
                const expectedFinalState = { shoulder: 90.0, elbow: -60.0, wrist: 15.0 };
                expect(finalState).toEqual(expectedFinalState);

            } finally {
                await consumer.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("multiple consumers same room", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            // Create multiple consumers
            const consumer1 = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);
            const consumer2 = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                // Set up message collection for both consumers
                const consumer1Collector = new MessageCollector(1);
                const consumer2Collector = new MessageCollector(1);

                consumer1.onJointUpdate(consumer1Collector.collect);
                consumer2.onJointUpdate(consumer2Collector.collect);

                // Wait for connections
                await sleep(200);

                // Producer sends updates
                const testJoints = [
                    { name: "joint1", value: 10.0 },
                    { name: "joint2", value: 20.0 }
                ];
                await producer.sendJointUpdate(testJoints);

                // Wait for message propagation
                const consumer1Updates = await consumer1Collector.waitForMessages(2000);
                const consumer2Updates = await consumer2Collector.waitForMessages(2000);

                // Both consumers should receive the same update
                expect(consumer1Updates.length).toBeGreaterThanOrEqual(1);
                expect(consumer2Updates.length).toBeGreaterThanOrEqual(1);

                // Verify both received same data
                if (consumer1Updates.length > 0 && consumer2Updates.length > 0) {
                    expect(consumer1Updates[consumer1Updates.length - 1]).toEqual(
                        consumer2Updates[consumer2Updates.length - 1]
                    );
                }

            } finally {
                await consumer1.disconnect();
                await consumer2.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("emergency stop propagation", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            // Create consumers
            const consumer1 = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);
            const consumer2 = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                // Set up error collection
                const consumer1ErrorCollector = new MessageCollector<string>(1);
                const consumer2ErrorCollector = new MessageCollector<string>(1);

                consumer1.onError(consumer1ErrorCollector.collect);
                consumer2.onError(consumer2ErrorCollector.collect);

                // Wait for connections
                await sleep(200);

                // Producer sends emergency stop
                await producer.sendEmergencyStop("Integration test emergency stop");

                // Wait for message propagation
                const consumer1Errors = await consumer1ErrorCollector.waitForMessages(2000);
                const consumer2Errors = await consumer2ErrorCollector.waitForMessages(2000);

                // Both consumers should receive emergency stop
                expect(consumer1Errors.length).toBeGreaterThanOrEqual(1);
                expect(consumer2Errors.length).toBeGreaterThanOrEqual(1);

                // Verify error messages contain emergency stop info
                if (consumer1Errors.length > 0) {
                    expect(consumer1Errors[consumer1Errors.length - 1].toLowerCase()).toContain("emergency stop");
                }
                if (consumer2Errors.length > 0) {
                    expect(consumer2Errors[consumer2Errors.length - 1].toLowerCase()).toContain("emergency stop");
                }

            } finally {
                await consumer1.disconnect();
                await consumer2.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("producer reconnection workflow", async () => {
        // Create room first
        const tempProducer = new RoboticsProducer(TEST_SERVER_URL);
        const { workspaceId, roomId } = await tempProducer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        try {
            // Create consumer first
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                const updateCollector = new MessageCollector(2);
                consumer.onJointUpdate(updateCollector.collect);

                // Create producer and connect
                const producer = new RoboticsProducer(TEST_SERVER_URL);
                await producer.connect(workspaceId, roomId);

                // Send initial update
                await producer.sendStateSync({ joint1: 10.0 });
                await sleep(100);

                // Disconnect producer
                await producer.disconnect();

                // Reconnect producer
                await producer.connect(workspaceId, roomId);

                // Send another update
                await producer.sendStateSync({ joint1: 20.0 });
                await sleep(200);

                // Consumer should have received both updates
                const receivedUpdates = await updateCollector.waitForMessages(3000);
                expect(receivedUpdates.length).toBeGreaterThanOrEqual(2);

                await producer.disconnect();

            } finally {
                await consumer.disconnect();
            }
        } finally {
            await roomManager.cleanup(tempProducer);
        }
    });

    test("consumer late join", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            // Producer sends some updates before consumer joins
            await producer.sendStateSync({ joint1: 10.0, joint2: 20.0 });
            await sleep(100);

            await producer.sendJointUpdate([{ name: "joint3", value: 30.0 }]);
            await sleep(100);

            // Now consumer joins
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                // Consumer should be able to get current state
                const currentState = await consumer.getStateSyncAsync();

                // Should contain all previously sent updates
                const expectedState = { joint1: 10.0, joint2: 20.0, joint3: 30.0 };
                expect(currentState).toEqual(expectedState);

            } finally {
                await consumer.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("room cleanup on producer disconnect", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                // Send some state
                await producer.sendStateSync({ joint1: 42.0 });
                await sleep(100);

                // Verify state exists
                const stateBefore = await consumer.getStateSyncAsync();
                expect(stateBefore).toEqual({ joint1: 42.0 });

                // Producer disconnects
                await producer.disconnect();
                await sleep(100);

                // State should still be accessible to consumer
                const stateAfter = await consumer.getStateSyncAsync();
                expect(stateAfter).toEqual({ joint1: 42.0 });

            } finally {
                await consumer.disconnect();
            }
        } finally {
            // Room cleanup handled by roomManager since producer disconnected
        }
    });

    test("high frequency updates", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            try {
                const updateCollector = new MessageCollector(5);
                consumer.onJointUpdate(updateCollector.collect);

                // Wait for connection
                await sleep(100);

                // Send rapid updates
                for (let i = 0; i < 20; i++) {
                    await producer.sendStateSync({ joint1: i, timestamp: i });
                    await sleep(10); // 10ms intervals
                }

                // Wait for all messages
                const receivedUpdates = await updateCollector.waitForMessages(5000);

                // Should have received multiple updates
                // (exact number may vary due to change detection)
                expect(receivedUpdates.length).toBeGreaterThanOrEqual(5);

                // Final state should reflect last update
                const finalState = await consumer.getStateSyncAsync();
                expect(finalState.joint1).toBe(19);
                expect(finalState.timestamp).toBe(19);

            } finally {
                await consumer.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });
}); 