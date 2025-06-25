/**
 * Test setup and utilities for RobotHub TransportServer JS Client Tests
 * Equivalent to Python's conftest.py
 */
import { expect } from "bun:test";

// Default server URL for tests
export const TEST_SERVER_URL = "http://localhost:8000";

// Test timeout configuration
export const TEST_TIMEOUT = 10000; // 10 seconds

// Helper to generate test IDs
export function generateTestId(prefix: string = "test"): string {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Helper to wait for async operations
export function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Test workspace and room management
export class TestRoomManager {
    private createdRooms: Array<{ workspaceId: string; roomId: string }> = [];

    addRoom(workspaceId: string, roomId: string) {
        this.createdRooms.push({ workspaceId, roomId });
    }

    async cleanup(client: any) {
        for (const { workspaceId, roomId } of this.createdRooms) {
            try {
                await client.deleteRoom(workspaceId, roomId);
            } catch (error) {
                // Ignore cleanup errors
                console.warn(`Failed to cleanup room ${roomId}:`, error);
            }
        }
        this.createdRooms = [];
    }
}

// Mock frame source for video tests
export async function mockFrameSource(): Promise<ArrayBuffer | null> {
    // Create a simple test frame (RGBA data)
    const width = 320;
    const height = 240;
    const size = width * height * 4; // RGBA
    const buffer = new ArrayBuffer(size);
    const view = new Uint8Array(buffer);
    
    // Fill with test pattern
    for (let i = 0; i < size; i += 4) {
        view[i] = 255;     // R
        view[i + 1] = 0;   // G
        view[i + 2] = 0;   // B
        view[i + 3] = 255; // A
    }
    
    return buffer;
}

// Test assertion helpers
export function assertIsConnected(client: any, workspaceId: string, roomId: string) {
    if (!client.isConnected()) {
        throw new Error("Expected client to be connected");
    }
    const info = client.getConnectionInfo();
    if (!info.connected) {
        throw new Error("Expected connection info to show connected");
    }
    if (info.workspace_id !== workspaceId) {
        throw new Error(`Expected workspace_id ${workspaceId}, got ${info.workspace_id}`);
    }
    if (info.room_id !== roomId) {
        throw new Error(`Expected room_id ${roomId}, got ${info.room_id}`);
    }
}

export function assertIsDisconnected(client: any) {
    if (client.isConnected()) {
        throw new Error("Expected client to be disconnected");
    }
    const info = client.getConnectionInfo();
    if (info.connected) {
        throw new Error("Expected connection info to show disconnected");
    }
}

// Message collection helper for testing callbacks
export class MessageCollector<T = any> {
    private messages: T[] = [];
    private promise: Promise<T[]> | null = null;
    private resolve: ((value: T[]) => void) | null = null;

    constructor(private expectedCount: number = 1) {}

    collect = (message: T) => {
        this.messages.push(message);
        if (this.messages.length >= this.expectedCount && this.resolve) {
            this.resolve([...this.messages]);
        }
    };

    async waitForMessages(timeoutMs: number = 5000): Promise<T[]> {
        if (this.messages.length >= this.expectedCount) {
            return [...this.messages];
        }

        this.promise = new Promise((resolve, reject) => {
            this.resolve = resolve;
            setTimeout(() => {
                reject(new Error(`Timeout waiting for ${this.expectedCount} messages, got ${this.messages.length}`));
            }, timeoutMs);
        });

        return this.promise;
    }

    getMessages(): T[] {
        return [...this.messages];
    }

    clear() {
        this.messages = [];
        this.promise = null;
        this.resolve = null;
    }
} 