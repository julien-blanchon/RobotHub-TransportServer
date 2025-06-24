/**
 * Consumer client for receiving robot commands in RobotHub TransportServer
 */
import { RoboticsClientCore } from './core.js';
import type { WebSocketMessage, ClientOptions, JointUpdateCallback, StateSyncCallback } from './types.js';
export declare class RoboticsConsumer extends RoboticsClientCore {
    private onStateSyncCallback;
    private onJointUpdateCallback;
    constructor(baseUrl?: string, options?: ClientOptions);
    connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean>;
    getStateSyncAsync(): Promise<Record<string, number>>;
    onStateSync(callback: StateSyncCallback): void;
    onJointUpdate(callback: JointUpdateCallback): void;
    protected handleRoleSpecificMessage(message: WebSocketMessage): void;
    private handleStateSync;
    private handleJointUpdate;
    /**
     * Create a consumer and automatically connect to a room
     */
    static createAndConnect(workspaceId: string, roomId: string, baseUrl?: string, participantId?: string): Promise<RoboticsConsumer>;
}
