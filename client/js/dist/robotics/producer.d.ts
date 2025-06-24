/**
 * Producer client for controlling robots in RobotHub TransportServer
 */
import { RoboticsClientCore } from './core.js';
import type { JointData, WebSocketMessage, ClientOptions } from './types.js';
export declare class RoboticsProducer extends RoboticsClientCore {
    constructor(baseUrl?: string, options?: ClientOptions);
    connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean>;
    sendJointUpdate(joints: JointData[]): Promise<void>;
    sendStateSync(state: Record<string, number>): Promise<void>;
    sendEmergencyStop(reason?: string): Promise<void>;
    protected handleRoleSpecificMessage(message: WebSocketMessage): void;
    /**
     * Create a room and automatically connect as producer
     */
    static createAndConnect(baseUrl?: string, workspaceId?: string, roomId?: string, participantId?: string): Promise<RoboticsProducer>;
    /**
     * Get the current room ID (useful when auto-created)
     */
    get currentRoomId(): string | null;
}
