/**
 * Tests for RoboticsProducer - equivalent to Python's test_producer.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { robotics } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager, MessageCollector, sleep, assertIsConnected, assertIsDisconnected } from "./setup";

const { RoboticsProducer } = robotics;

describe("RoboticsProducer", () => {
    let producer: robotics.RoboticsProducer;
    let roomManager: TestRoomManager;

    beforeEach(() => {
        producer = new RoboticsProducer(TEST_SERVER_URL);
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        if (producer.isConnected()) {
            await producer.disconnect();
        }
        await roomManager.cleanup(producer);
    });

    test("producer connection", async () => {
        // Create room first
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        expect(producer.isConnected()).toBe(false);

        const success = await producer.connect(workspaceId, roomId);
        expect(success).toBe(true);
        assertIsConnected(producer, workspaceId, roomId);

        const info = producer.getConnectionInfo();
        expect(info.role).toBe("producer");

        await producer.disconnect();
        assertIsDisconnected(producer);
    });

    test("producer connection info", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        const info = producer.getConnectionInfo();
        expect(info.connected).toBe(true);
        expect(info.room_id).toBe(roomId);
        expect(info.workspace_id).toBe(workspaceId);
        expect(info.role).toBe("producer");
        expect(info.participant_id).toBeTruthy();
        expect(info.base_url).toBe(TEST_SERVER_URL);
    });

    test("send joint update", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        const joints = [
            { name: "shoulder", value: 45.0 },
            { name: "elbow", value: -20.0 },
            { name: "wrist", value: 10.0 }
        ];

        // Should not throw an exception
        await producer.sendJointUpdate(joints);
    });

    test("send state sync", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        const state = { shoulder: 45.0, elbow: -20.0, wrist: 10.0 };

        // Should not throw an exception
        await producer.sendStateSync(state);
    });

    test("send emergency stop", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        // Should not throw an exception
        await producer.sendEmergencyStop("Test emergency stop");
        await producer.sendEmergencyStop(); // Default reason
    });

    test("producer callbacks", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        let connectedCalled = false;
        let disconnectedCalled = false;
        let errorCalled = false;
        let errorMessage: string | null = null;

        producer.onConnected(() => {
            connectedCalled = true;
        });

        producer.onDisconnected(() => {
            disconnectedCalled = true;
        });

        producer.onError((error) => {
            errorCalled = true;
            errorMessage = error;
        });

        // Connect and disconnect
        await producer.connect(workspaceId, roomId);
        await sleep(100); // Give callbacks time to execute
        expect(connectedCalled).toBe(true);

        await producer.disconnect();
        await sleep(100); // Give callbacks time to execute
        expect(disconnectedCalled).toBe(true);
    });

    test("send without connection", async () => {
        expect(producer.isConnected()).toBe(false);

        await expect(producer.sendJointUpdate([{ name: "test", value: 0 }]))
            .rejects.toThrow("Must be connected");

        await expect(producer.sendStateSync({ test: 0 }))
            .rejects.toThrow("Must be connected");

        await expect(producer.sendEmergencyStop())
            .rejects.toThrow("Must be connected");
    });

    test("multiple connections", async () => {
        // Connect to first room
        const { workspaceId: workspaceId1, roomId: roomId1 } = await producer.createRoom();
        roomManager.addRoom(workspaceId1, roomId1);
        await producer.connect(workspaceId1, roomId1);
        
        expect(producer.getConnectionInfo().room_id).toBe(roomId1);
        expect(producer.getConnectionInfo().workspace_id).toBe(workspaceId1);

        // Create second room
        const { workspaceId: workspaceId2, roomId: roomId2 } = await producer.createRoom();
        roomManager.addRoom(workspaceId2, roomId2);

        // Connect to second room (should disconnect from first)
        await producer.connect(workspaceId2, roomId2);
        expect(producer.getConnectionInfo().room_id).toBe(roomId2);
        expect(producer.getConnectionInfo().workspace_id).toBe(workspaceId2);
        expect(producer.isConnected()).toBe(true);
    });

    test("duplicate producer connection", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        
        const producer2 = new RoboticsProducer(TEST_SERVER_URL);

        try {
            // First producer connects successfully
            const success1 = await producer.connect(workspaceId, roomId);
            expect(success1).toBe(true);

            // Second producer should fail to connect as producer
            const success2 = await producer2.connect(workspaceId, roomId);
            expect(success2).toBe(false); // Should fail since room already has producer
        } finally {
            if (producer2.isConnected()) {
                await producer2.disconnect();
            }
        }
    });

    test("custom participant id", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        const customId = "custom-producer-123";

        await producer.connect(workspaceId, roomId, customId);

        const info = producer.getConnectionInfo();
        expect(info.participant_id).toBe(customId);
    });

    test("large joint update", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        // Create a large joint update
        const joints = Array.from({ length: 100 }, (_, i) => ({
            name: `joint_${i}`,
            value: i
        }));

        // Should handle large updates without issue
        await producer.sendJointUpdate(joints);
    });

    test("rapid updates", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);
        await producer.connect(workspaceId, roomId);

        // Send multiple rapid updates
        for (let i = 0; i < 10; i++) {
            await producer.sendStateSync({ joint1: i, joint2: i * 2 });
            await sleep(10); // Small delay
        }
    });
}); 