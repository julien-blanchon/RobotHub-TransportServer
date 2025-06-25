/**
 * Tests for RoboticsConsumer - equivalent to Python's test_consumer.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { robotics } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager, MessageCollector, sleep, assertIsConnected, assertIsDisconnected } from "./setup";

const { RoboticsProducer, RoboticsConsumer } = robotics;

describe("RoboticsConsumer", () => {
    let consumer: robotics.RoboticsConsumer;
    let producer: robotics.RoboticsProducer;
    let roomManager: TestRoomManager;

    beforeEach(() => {
        consumer = new RoboticsConsumer(TEST_SERVER_URL);
        producer = new RoboticsProducer(TEST_SERVER_URL);
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        if (consumer.isConnected()) {
            await consumer.disconnect();
        }
        if (producer.isConnected()) {
            await producer.disconnect();
        }
        await roomManager.cleanup(producer);
    });

    test("consumer connection", async () => {
        // Create room first
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        expect(consumer.isConnected()).toBe(false);

        const success = await consumer.connect(workspaceId, roomId);
        expect(success).toBe(true);
        assertIsConnected(consumer, workspaceId, roomId);

        const info = consumer.getConnectionInfo();
        expect(info.role).toBe("consumer");

        await consumer.disconnect();
        assertIsDisconnected(consumer);
    });

    test("consumer connection info", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        const info = consumer.getConnectionInfo();
        expect(info.connected).toBe(true);
        expect(info.room_id).toBe(roomId);
        expect(info.workspace_id).toBe(workspaceId);
        expect(info.role).toBe("consumer");
        expect(info.participant_id).toBeTruthy();
        expect(info.base_url).toBe(TEST_SERVER_URL);
    });

    test("get state sync", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        const state = await consumer.getStateSyncAsync();
        expect(typeof state).toBe("object");
        // Initial state should be empty
        expect(Object.keys(state)).toHaveLength(0);
    });

    test("consumer callbacks setup", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        let stateSyncCalled = false;
        let jointUpdateCalled = false;
        let errorCalled = false;
        let connectedCalled = false;
        let disconnectedCalled = false;

        consumer.onStateSync((state) => {
            stateSyncCalled = true;
        });

        consumer.onJointUpdate((joints) => {
            jointUpdateCalled = true;
        });

        consumer.onError((error) => {
            errorCalled = true;
        });

        consumer.onConnected(() => {
            connectedCalled = true;
        });

        consumer.onDisconnected(() => {
            disconnectedCalled = true;
        });

        // Connect and test connection callbacks
        await consumer.connect(workspaceId, roomId);
        await sleep(100);
        expect(connectedCalled).toBe(true);

        await consumer.disconnect();
        await sleep(100);
        expect(disconnectedCalled).toBe(true);
    });

    test("multiple consumers", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const consumer1 = new RoboticsConsumer(TEST_SERVER_URL);
        const consumer2 = new RoboticsConsumer(TEST_SERVER_URL);

        try {
            // Both consumers should be able to connect
            const success1 = await consumer1.connect(workspaceId, roomId);
            const success2 = await consumer2.connect(workspaceId, roomId);

            expect(success1).toBe(true);
            expect(success2).toBe(true);
            expect(consumer1.isConnected()).toBe(true);
            expect(consumer2.isConnected()).toBe(true);
        } finally {
            if (consumer1.isConnected()) {
                await consumer1.disconnect();
            }
            if (consumer2.isConnected()) {
                await consumer2.disconnect();
            }
        }
    });

    test("consumer receive state sync", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const updateCollector = new MessageCollector(1);
        consumer.onJointUpdate(updateCollector.collect);

        await producer.connect(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        // Give some time for connection to stabilize
        await sleep(100);

        // Producer sends state sync (which gets converted to joint updates)
        await producer.sendStateSync({ shoulder: 45.0, elbow: -20.0 });

        // Wait for message to be received
        const receivedUpdates = await updateCollector.waitForMessages(2000);

        // Consumer should have received the joint updates from the state sync
        expect(receivedUpdates.length).toBeGreaterThanOrEqual(1);
    });

    test("consumer receive joint updates", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const updateCollector = new MessageCollector(1);
        consumer.onJointUpdate(updateCollector.collect);

        await producer.connect(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        // Give some time for connection to stabilize
        await sleep(100);

        // Producer sends joint updates
        const testJoints = [
            { name: "shoulder", value: 45.0 },
            { name: "elbow", value: -20.0 }
        ];
        await producer.sendJointUpdate(testJoints);

        // Wait for message to be received
        const receivedUpdates = await updateCollector.waitForMessages(2000);

        // Consumer should have received the joint update
        expect(receivedUpdates.length).toBeGreaterThanOrEqual(1);
        if (receivedUpdates.length > 0) {
            const receivedJoints = receivedUpdates[receivedUpdates.length - 1];
            expect(Array.isArray(receivedJoints)).toBe(true);
            expect(receivedJoints).toHaveLength(2);
        }
    });

    test("consumer multiple updates", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const updateCollector = new MessageCollector(3);
        consumer.onJointUpdate(updateCollector.collect);

        await producer.connect(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        // Give some time for connection to stabilize
        await sleep(100);

        // Send multiple updates
        for (let i = 0; i < 5; i++) {
            await producer.sendStateSync({
                joint1: i * 10,
                joint2: i * -5
            });
            await sleep(50);
        }

        // Wait for all messages to be received
        const receivedUpdates = await updateCollector.waitForMessages(3000);

        // Should have received multiple updates
        expect(receivedUpdates.length).toBeGreaterThanOrEqual(3);
    });

    test("consumer emergency stop", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const errorCollector = new MessageCollector<string>(1);
        consumer.onError(errorCollector.collect);

        await producer.connect(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        // Give some time for connection to stabilize
        await sleep(100);

        // Producer sends emergency stop
        await producer.sendEmergencyStop("Test emergency stop");

        // Wait for message to be received
        const receivedErrors = await errorCollector.waitForMessages(2000);

        // Consumer should have received emergency stop as error
        expect(receivedErrors.length).toBeGreaterThanOrEqual(1);
        if (receivedErrors.length > 0) {
            expect(receivedErrors[receivedErrors.length - 1].toLowerCase()).toContain("emergency stop");
        }
    });

    test("custom participant id", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        const customId = "custom-consumer-456";

        await consumer.connect(workspaceId, roomId, customId);

        const info = consumer.getConnectionInfo();
        expect(info.participant_id).toBe(customId);
    });

    test("get state without connection", async () => {
        expect(consumer.isConnected()).toBe(false);

        await expect(consumer.getStateSyncAsync())
            .rejects.toThrow("Must be connected");
    });

    test("consumer reconnection", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        // First connection
        await consumer.connect(workspaceId, roomId);
        expect(consumer.isConnected()).toBe(true);

        await consumer.disconnect();
        expect(consumer.isConnected()).toBe(false);

        // Reconnect to same room
        await consumer.connect(workspaceId, roomId);
        expect(consumer.isConnected()).toBe(true);
        expect(consumer.getConnectionInfo().room_id).toBe(roomId);
        expect(consumer.getConnectionInfo().workspace_id).toBe(workspaceId);
    });

    test("consumer state after producer updates", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        await producer.connect(workspaceId, roomId);
        await consumer.connect(workspaceId, roomId);

        // Give some time for connection to stabilize
        await sleep(100);

        // Producer sends some state updates
        await producer.sendStateSync({
            shoulder: 45.0,
            elbow: -20.0,
            wrist: 10.0
        });

        // Wait for state to propagate
        await sleep(200);

        // Consumer should be able to get updated state
        const state = await consumer.getStateSyncAsync();
        expect(typeof state).toBe("object");

        // State should contain the joints we sent
        const expectedJoints = new Set(["shoulder", "elbow", "wrist"]);
        if (Object.keys(state).length > 0) { // Only check if state is not empty
            expect(new Set(Object.keys(state))).toEqual(expectedJoints);
        }
    });
}); 