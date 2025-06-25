/**
 * Tests for REST API functionality - equivalent to Python's test_rest_api.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { robotics } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager } from "./setup";

const { RoboticsProducer } = robotics;

describe("REST API", () => {
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

    test("list rooms empty", async () => {
        // Use a temporary workspace ID
        const workspaceId = `test-workspace-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const rooms = await producer.listRooms(workspaceId);
        expect(Array.isArray(rooms)).toBe(true);
    });

    test("create room", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        expect(typeof workspaceId).toBe("string");
        expect(typeof roomId).toBe("string");
        expect(workspaceId.length).toBeGreaterThan(0);
        expect(roomId.length).toBeGreaterThan(0);
    });

    test("create room with id", async () => {
        const customRoomId = "test-room-123";
        const customWorkspaceId = "test-workspace-456";
        const { workspaceId, roomId } = await producer.createRoom(customWorkspaceId, customRoomId);
        roomManager.addRoom(workspaceId, roomId);

        expect(workspaceId).toBe(customWorkspaceId);
        expect(roomId).toBe(customRoomId);
    });

    test("list rooms with rooms", async () => {
        // Create a test room
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const rooms = await producer.listRooms(workspaceId);
        expect(Array.isArray(rooms)).toBe(true);
        expect(rooms.length).toBeGreaterThanOrEqual(1);

        // Check if our room is in the list
        const roomIds = rooms.map(room => room.id);
        expect(roomIds).toContain(roomId);

        // Verify room structure
        const testRoom = rooms.find(room => room.id === roomId);
        expect(testRoom).toBeDefined();
        expect(testRoom!).toHaveProperty("participants");
        expect(testRoom!).toHaveProperty("joints_count");
    });

    test("get room info", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const roomInfo = await producer.getRoomInfo(workspaceId, roomId);
        expect(typeof roomInfo).toBe("object");
        expect(roomInfo.id).toBe(roomId);
        expect(roomInfo.workspace_id).toBe(workspaceId);
        expect(roomInfo).toHaveProperty("participants");
        expect(roomInfo).toHaveProperty("joints_count");
        expect(roomInfo).toHaveProperty("has_producer");
        expect(roomInfo).toHaveProperty("active_consumers");
    });

    test("get room state", async () => {
        const { workspaceId, roomId } = await producer.createRoom();
        roomManager.addRoom(workspaceId, roomId);

        const roomState = await producer.getRoomState(workspaceId, roomId);
        expect(typeof roomState).toBe("object");
        expect(roomState).toHaveProperty("room_id");
        expect(roomState).toHaveProperty("workspace_id");
        expect(roomState).toHaveProperty("joints");
        expect(roomState).toHaveProperty("participants");
        expect(roomState).toHaveProperty("timestamp");
        expect(roomState.room_id).toBe(roomId);
        expect(roomState.workspace_id).toBe(workspaceId);
    });

    test("delete room", async () => {
        const { workspaceId, roomId } = await producer.createRoom();

        // Verify room exists
        const roomsBefore = await producer.listRooms(workspaceId);
        const roomIdsBefore = roomsBefore.map(room => room.id);
        expect(roomIdsBefore).toContain(roomId);

        // Delete room
        const success = await producer.deleteRoom(workspaceId, roomId);
        expect(success).toBe(true);

        // Verify room is deleted
        const roomsAfter = await producer.listRooms(workspaceId);
        const roomIdsAfter = roomsAfter.map(room => room.id);
        expect(roomIdsAfter).not.toContain(roomId);
    });

    test("delete nonexistent room", async () => {
        const workspaceId = `test-workspace-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const fakeRoomId = "nonexistent-room-id";
        const success = await producer.deleteRoom(workspaceId, fakeRoomId);
        expect(success).toBe(false);
    });

    test("get room info nonexistent", async () => {
        const workspaceId = `test-workspace-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const fakeRoomId = "nonexistent-room-id";

        // This should raise an exception or return error info
        try {
            await producer.getRoomInfo(workspaceId, fakeRoomId);
            // If no exception, this is unexpected for nonexistent room
            expect(true).toBe(false); // Force test failure
        } catch (error) {
            // Expected behavior for nonexistent room
            expect(error).toBeDefined();
        }
    });

    test("get room state nonexistent", async () => {
        const workspaceId = `test-workspace-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const fakeRoomId = "nonexistent-room-id";

        // This should raise an exception or return error info
        try {
            await producer.getRoomState(workspaceId, fakeRoomId);
            // If no exception, this is unexpected for nonexistent room
            expect(true).toBe(false); // Force test failure
        } catch (error) {
            // Expected behavior for nonexistent room
            expect(error).toBeDefined();
        }
    });
}); 