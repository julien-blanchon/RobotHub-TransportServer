/**
 * Core video client for RobotHub TransportServer
 * Base class providing REST API, WebSocket, and WebRTC functionality
 */
import { EventEmitter } from 'eventemitter3';
import type { ParticipantRole, RoomInfo, RoomState, ConnectionInfo, WebSocketMessage, WebRTCSignalResponse, ClientOptions, WebRTCConfig, WebRTCStats, VideoConfig, RecoveryConfig, ErrorCallback, ConnectedCallback, DisconnectedCallback } from './types.js';
export declare class VideoClientCore extends EventEmitter {
    protected baseUrl: string;
    protected apiBase: string;
    protected websocket: WebSocket | null;
    protected peerConnection: RTCPeerConnection | null;
    protected localStream: MediaStream | null;
    protected remoteStream: MediaStream | null;
    protected workspaceId: string | null;
    protected roomId: string | null;
    protected role: ParticipantRole | null;
    protected participantId: string | null;
    protected connected: boolean;
    protected options: ClientOptions;
    protected webrtcConfig: WebRTCConfig;
    protected onErrorCallback: ErrorCallback | null;
    protected onConnectedCallback: ConnectedCallback | null;
    protected onDisconnectedCallback: DisconnectedCallback | null;
    constructor(baseUrl: string, options?: ClientOptions);
    listRooms(workspaceId: string): Promise<RoomInfo[]>;
    createRoom(workspaceId?: string, roomId?: string, config?: VideoConfig, recoveryConfig?: RecoveryConfig): Promise<{
        workspaceId: string;
        roomId: string;
    }>;
    deleteRoom(workspaceId: string, roomId: string): Promise<boolean>;
    getRoomState(workspaceId: string, roomId: string): Promise<RoomState>;
    getRoomInfo(workspaceId: string, roomId: string): Promise<RoomInfo>;
    sendWebRTCSignal(workspaceId: string, roomId: string, clientId: string, message: RTCSessionDescriptionInit | RTCIceCandidateInit | Record<string, unknown>): Promise<WebRTCSignalResponse>;
    connectToRoom(workspaceId: string, roomId: string, role: ParticipantRole, participantId?: string): Promise<boolean>;
    disconnect(): Promise<void>;
    createPeerConnection(): RTCPeerConnection;
    createOffer(): Promise<RTCSessionDescriptionInit>;
    createAnswer(offer: RTCSessionDescriptionInit): Promise<RTCSessionDescriptionInit>;
    setRemoteDescription(description: RTCSessionDescriptionInit): Promise<void>;
    addIceCandidate(candidate: RTCIceCandidateInit): Promise<void>;
    startProducing(constraints?: MediaStreamConstraints): Promise<MediaStream>;
    startScreenShare(): Promise<MediaStream>;
    stopProducing(): void;
    getLocalStream(): MediaStream | null;
    getRemoteStream(): MediaStream | null;
    getPeerConnection(): RTCPeerConnection | null;
    getStats(): Promise<WebRTCStats | null>;
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
    private extractVideoStats;
    protected generateWorkspaceId(): string;
}
