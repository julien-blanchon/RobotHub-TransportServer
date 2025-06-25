/**
 * Tests for Factory Functions - equivalent to Python's test_factory_functions.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { robotics } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager, MessageCollector, sleep } from "./setup";

const { RoboticsProducer, RoboticsConsumer, createClient, createProducerClient, createConsumerClient } = robotics;

describe("Factory Functions", () => {
    let roomManager: TestRoomManager;

    beforeEach(() => {
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        // Cleanup will be handled by individual tests
    });

    test("create client producer", () => {
        const client = createClient("producer");
        expect(client).toBeInstanceOf(RoboticsProducer);
        expect(client.isConnected()).toBe(false);
        expect(client.getConnectionInfo().base_url).toBe("http://localhost:8000");
    });

    test("create client consumer", () => {
        const client = createClient("consumer");
        expect(client).toBeInstanceOf(RoboticsConsumer);
        expect(client.isConnected()).toBe(false);
        expect(client.getConnectionInfo().base_url).toBe("http://localhost:8000");
    });

    test("create client invalid role", () => {
        expect(() => createClient("invalid_role" as any)).toThrow("Invalid role");
    });

    test("create client default url", () => {
        const client = createClient("producer");
        expect(client.getConnectionInfo().base_url).toBe("http://localhost:8000");
    });

    test("create producer client auto room", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        
        try {
            expect(producer).toBeInstanceOf(RoboticsProducer);
            expect(producer.isConnected()).toBe(true);
            const info = producer.getConnectionInfo();
            expect(info.room_id).toBeTruthy();
            expect(info.workspace_id).toBeTruthy();
            expect(info.role).toBe("producer");

            // Should be able to send commands immediately
            await producer.sendStateSync({ test: 123.0 });

            // Track for cleanup
            roomManager.addRoom(info.workspace_id!, info.room_id!);
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("create producer client specific room", async () => {
        // First create a room
        const tempProducer = new RoboticsProducer(TEST_SERVER_URL);
        const { workspaceId, roomId } = await tempProducer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        try {
            const producer = await createProducerClient(TEST_SERVER_URL, workspaceId, roomId);

            expect(producer).toBeInstanceOf(RoboticsProducer);
            expect(producer.isConnected()).toBe(true);
            const info = producer.getConnectionInfo();
            expect(info.room_id).toBe(roomId);
            expect(info.workspace_id).toBe(workspaceId);
            expect(info.role).toBe("producer");

            await producer.disconnect();
        } finally {
            await roomManager.cleanup(tempProducer);
        }
    });

    test("create consumer client", async () => {
        // First create a room
        const tempProducer = new RoboticsProducer(TEST_SERVER_URL);
        const { workspaceId, roomId } = await tempProducer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        try {
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            expect(consumer).toBeInstanceOf(RoboticsConsumer);
            expect(consumer.isConnected()).toBe(true);
            const info = consumer.getConnectionInfo();
            expect(info.room_id).toBe(roomId);
            expect(info.workspace_id).toBe(workspaceId);
            expect(info.role).toBe("consumer");

            // Should be able to get state immediately
            const state = await consumer.getStateSyncAsync();
            expect(typeof state).toBe("object");

            await consumer.disconnect();
        } finally {
            await roomManager.cleanup(tempProducer);
        }
    });

    test("create producer consumer pair", async () => {
        const producer = await createProducerClient(TEST_SERVER_URL);
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            const consumer = await createConsumerClient(workspaceId, roomId, TEST_SERVER_URL);

            // Both should be connected to same room
            const consumerInfo = consumer.getConnectionInfo();
            expect(producerInfo.room_id).toBe(consumerInfo.room_id);
            expect(producerInfo.workspace_id).toBe(consumerInfo.workspace_id);
            expect(producer.isConnected()).toBe(true);
            expect(consumer.isConnected()).toBe(true);

            // Test communication
            const updateCollector = new MessageCollector(1);
            consumer.onJointUpdate(updateCollector.collect);

            // Give some time for connection to stabilize
            await sleep(100);

            // Send update from producer
            await producer.sendStateSync({ test_joint: 42.0 });

            // Wait for message
            const receivedUpdates = await updateCollector.waitForMessages(2000);

            // Consumer should have received update
            expect(receivedUpdates.length).toBeGreaterThanOrEqual(1);

            await consumer.disconnect();
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("convenience functions with default url", async () => {
        const producer = await createProducerClient();
        const producerInfo = producer.getConnectionInfo();
        const workspaceId = producerInfo.workspace_id!;
        const roomId = producerInfo.room_id!;
        roomManager.addRoom(workspaceId, roomId);

        try {
            expect(producerInfo.base_url).toBe("http://localhost:8000");
            expect(producer.isConnected()).toBe(true);

            const consumer = await createConsumerClient(workspaceId, roomId);

            try {
                const consumerInfo = consumer.getConnectionInfo();
                expect(consumerInfo.base_url).toBe("http://localhost:8000");
                expect(consumer.isConnected()).toBe(true);
            } finally {
                await consumer.disconnect();
            }
        } finally {
            await producer.disconnect();
            await roomManager.cleanup(producer);
        }
    });

    test("multiple convenience producers", async () => {
        const producer1 = await createProducerClient(TEST_SERVER_URL);
        const producer2 = await createProducerClient(TEST_SERVER_URL);

        try {
            const info1 = producer1.getConnectionInfo();
            const info2 = producer2.getConnectionInfo();

            // Both should be connected to different rooms
            expect(info1.room_id).not.toBe(info2.room_id);
            expect(producer1.isConnected()).toBe(true);
            expect(producer2.isConnected()).toBe(true);

            // Track for cleanup
            roomManager.addRoom(info1.workspace_id!, info1.room_id!);
            roomManager.addRoom(info2.workspace_id!, info2.room_id!);

            // Both should work independently
            await producer1.sendStateSync({ joint1: 10.0 });
            await producer2.sendStateSync({ joint2: 20.0 });
        } finally {
            await producer1.disconnect();
            await producer2.disconnect();
            await roomManager.cleanup(producer1);
        }
    });

    test("create consumer nonexistent room", async () => {
        const fakeWorkspaceId = "00000000-0000-0000-0000-000000000000";
        const fakeRoomId = "00000000-0000-0000-0000-000000000000";

        const consumer = new RoboticsConsumer(TEST_SERVER_URL);
        const success = await consumer.connect(fakeWorkspaceId, fakeRoomId);

        // Should fail to connect to non-existent room
        expect(success).toBe(false);
        expect(consumer.isConnected()).toBe(false);
    });
}); 