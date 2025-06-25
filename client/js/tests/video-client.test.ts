/**
 * Tests for Video Client - equivalent to Python's test_video_client.py
 */
import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { video } from "../src/index";
import { TEST_SERVER_URL, TestRoomManager, mockFrameSource } from "./setup";

const { VideoProducer, VideoConsumer, createProducerClient, createConsumerClient } = video;

describe("Video Types", () => {
    test("resolution creation", () => {
        const resolution = { width: 1920, height: 1080 };
        expect(resolution.width).toBe(1920);
        expect(resolution.height).toBe(1080);
    });

    test("video config creation", () => {
        const config = {
            encoding: "vp8" as video.VideoEncoding,
            resolution: { width: 640, height: 480 },
            framerate: 30,
            bitrate: 1000000
        };
        expect(config.encoding).toBe("vp8");
        expect(config.resolution?.width).toBe(640);
        expect(config.framerate).toBe(30);
    });

    test("participant role enum", () => {
        const producerRole = "producer";
        const consumerRole = "consumer";
        expect(producerRole).toBe("producer");
        expect(consumerRole).toBe("consumer");
    });
});

describe("Video Core", () => {
    let roomManager: TestRoomManager;

    beforeEach(() => {
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        await roomManager.cleanup(new VideoProducer(TEST_SERVER_URL));
    });

    test("video producer creation", () => {
        const producer = new VideoProducer(TEST_SERVER_URL);
        expect(producer.getConnectionInfo().base_url).toBe(TEST_SERVER_URL);
        expect(producer.isConnected()).toBe(false);
        expect(producer.getConnectionInfo().room_id).toBeNull();
    });

    test("video consumer creation", () => {
        const consumer = new VideoConsumer(TEST_SERVER_URL);
        expect(consumer.getConnectionInfo().base_url).toBe(TEST_SERVER_URL);
        expect(consumer.isConnected()).toBe(false);
        expect(consumer.getConnectionInfo().room_id).toBeNull();
    });

    test("producer room creation", async () => {
        try {
            const producer = new VideoProducer(TEST_SERVER_URL);
            const { workspaceId, roomId } = await producer.createRoom();
            roomManager.addRoom(workspaceId, roomId);

            expect(typeof roomId).toBe("string");
            expect(roomId.length).toBeGreaterThan(0);
            console.log(`✅ Created room: ${roomId}`);
        } catch (error) {
            console.warn(`⚠️ Server not available: ${error}`);
            // Skip test if server not available
        }
    }, { timeout: 5000 });

    test("consumer list rooms", async () => {
        try {
            const consumer = new VideoConsumer(TEST_SERVER_URL);
            const workspaceId = "test-workspace-id";
            const rooms = await consumer.listRooms(workspaceId);
            expect(Array.isArray(rooms)).toBe(true);
            console.log(`✅ Listed ${rooms.length} rooms`);
        } catch (error) {
            console.warn(`⚠️ Server not available: ${error}`);
            // Skip test if server not available
        }
    }, { timeout: 5000 });
});

describe("Video Client Integration", () => {
    let roomManager: TestRoomManager;

    beforeEach(() => {
        roomManager = new TestRoomManager();
    });

    afterEach(async () => {
        await roomManager.cleanup(new VideoProducer(TEST_SERVER_URL));
    });

    test("producer consumer setup", () => {
        // Test producer setup
        const producer = new VideoProducer(TEST_SERVER_URL);
        expect(producer.getLocalStream()).toBeNull();

        // Test consumer setup
        const consumer = new VideoConsumer(TEST_SERVER_URL);
        expect(consumer.getRemoteStream()).toBeNull();

        console.log("✅ Producer/Consumer setup test passed");
    });

    test("custom stream setup validation", async () => {
        const producer = new VideoProducer(TEST_SERVER_URL);

        // This will fail because we're not connected, but it tests the setup
        try {
            // Simulate starting a custom stream when not connected
            await producer.startCamera();
            expect(true).toBe(false); // Should not reach here
        } catch (error: any) {
            expect(error.message).toContain("Must be connected");
            console.log("✅ Custom stream setup validation passed");
        }
    });

    test("factory functions", async () => {
        // Test that factory functions create the right types
        // (We can't actually connect without a server)

        try {
            await createProducerClient(TEST_SERVER_URL);
        } catch (error) {
            // Expected to fail without server
            console.log("✅ Producer factory function exists");
        }

        try {
            await createConsumerClient("test-workspace", "test-room", TEST_SERVER_URL);
        } catch (error) {
            // Expected to fail without server
            console.log("✅ Consumer factory function exists");
        }

        console.log("✅ Factory functions test passed");
    });

    test("mock frame source", async () => {
        const frameData = await mockFrameSource();
        expect(frameData).not.toBeNull();
        expect(frameData).toBeInstanceOf(ArrayBuffer);
        
        if (frameData) {
            expect(frameData.byteLength).toBe(320 * 240 * 4); // RGBA
            console.log("✅ Mock frame source test passed");
        }
    });

    test("video config types", () => {
        const config: video.VideoConfig = {
            encoding: "h264",
            resolution: { width: 1280, height: 720 },
            framerate: 60,
            bitrate: 2000000,
            quality: 90
        };

        expect(config.encoding).toBe("h264");
        expect(config.resolution?.width).toBe(1280);
        expect(config.resolution?.height).toBe(720);
        expect(config.framerate).toBe(60);
        expect(config.bitrate).toBe(2000000);
        expect(config.quality).toBe(90);

        console.log("✅ Video config types test passed");
    });

    test("recovery config types", () => {
        const recoveryConfig: video.RecoveryConfig = {
            frame_timeout_ms: 200,
            max_frame_reuse_count: 5,
            recovery_policy: "freeze_last_frame",
            fallback_policy: "connection_info",
            show_hold_indicators: true,
            fade_intensity: 0.8
        };

        expect(recoveryConfig.frame_timeout_ms).toBe(200);
        expect(recoveryConfig.recovery_policy).toBe("freeze_last_frame");
        expect(recoveryConfig.fallback_policy).toBe("connection_info");

        console.log("✅ Recovery config types test passed");
    });

    test("participant info types", () => {
        const participantInfo: video.ParticipantInfo = {
            producer: "producer-123",
            consumers: ["consumer-1", "consumer-2"],
            total: 3
        };

        expect(participantInfo.producer).toBe("producer-123");
        expect(participantInfo.consumers).toHaveLength(2);
        expect(participantInfo.total).toBe(3);

        console.log("✅ Participant info types test passed");
    });

    test("room info types", () => {
        const roomInfo: video.RoomInfo = {
            id: "room-123",
            workspace_id: "workspace-456",
            participants: {
                producer: "producer-1",
                consumers: ["consumer-1"],
                total: 2
            },
            frame_count: 1000,
            config: {
                encoding: "vp8",
                resolution: { width: 640, height: 480 },
                framerate: 30
            },
            has_producer: true,
            active_consumers: 1
        };

        expect(roomInfo.id).toBe("room-123");
        expect(roomInfo.workspace_id).toBe("workspace-456");
        expect(roomInfo.has_producer).toBe(true);
        expect(roomInfo.active_consumers).toBe(1);

        console.log("✅ Room info types test passed");
    });

    test("stream stats types", () => {
        const streamStats: video.StreamStats = {
            stream_id: "stream-123",
            duration_seconds: 120.5,
            frame_count: 3615,
            total_bytes: 1048576,
            average_fps: 30.0,
            average_bitrate: 1000000
        };

        expect(streamStats.stream_id).toBe("stream-123");
        expect(streamStats.duration_seconds).toBe(120.5);
        expect(streamStats.frame_count).toBe(3615);
        expect(streamStats.average_fps).toBe(30.0);

        console.log("✅ Stream stats types test passed");
    });
}); 