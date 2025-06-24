/**
 * Core robotics client for RobotHub TransportServer
 * Base class providing REST API and WebSocket functionality
 */
import { EventEmitter } from 'eventemitter3';
import type { ParticipantRole, RoomInfo, RoomState, ConnectionInfo, WebSocketMessage, ClientOptions, ErrorCallback, ConnectedCallback, DisconnectedCallback } from './types.js';
export declare class RoboticsClientCore extends EventEmitter {
    protected baseUrl: string;
    protected apiBase: string;
    protected websocket: WebSocket | null;
    protected workspaceId: string | null;
    protected roomId: string | null;
    protected role: ParticipantRole | null;
    protected participantId: string | null;
    protected connected: boolean;
    protected options: ClientOptions;
    protected onErrorCallback: ErrorCallback | null;
    protected onConnectedCallback: ConnectedCallback | null;
    protected onDisconnectedCallback: DisconnectedCallback | null;
    constructor(baseUrl?: string, options?: ClientOptions);
    listRooms(workspaceId: string): Promise<RoomInfo[]>;
    createRoom(workspaceId?: string, roomId?: string): Promise<{
        workspaceId: string;
        roomId: string;
    }>;
    deleteRoom(workspaceId: string, roomId: string): Promise<boolean>;
    getRoomState(workspaceId: string, roomId: string): Promise<RoomState>;
    getRoomInfo(workspaceId: string, roomId: string): Promise<RoomInfo>;
    connectToRoom(workspaceId: string, roomId: string, role: ParticipantRole, participantId?: string): Promise<boolean>;
    disconnect(): Promise<void>;
    protected sendJoinMessage(): void;
    protected handleMessage(message: WebSocketMessage): void;
    protected handleRoleSpecificMessage(message: WebSocketMessage): void;
    protected handleError(errorMessage: string): void;
    sendHeartbeat(): Promise<void>;
    isConnected(): boolean;
    getConnectionInfo(): ConnectionInfo;
    onError(callback: ErrorCallback): void;
    onConnected(callback: ConnectedCallback): void;
    onDisconnected(callback: DisconnectedCallback): void;
    private fetchApi;
    protected generateWorkspaceId(): string;
}
