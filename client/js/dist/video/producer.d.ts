/**
 * Producer client for video streaming in RobotHub TransportServer
 */
import { VideoClientCore } from './core.js';
import type { WebSocketMessage, ClientOptions, VideoConfig } from './types.js';
export declare class VideoProducer extends VideoClientCore {
    private consumerConnections;
    constructor(baseUrl: string, options?: ClientOptions);
    connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean>;
    private connectToExistingConsumers;
    private createPeerConnectionForConsumer;
    private restartConnectionToConsumer;
    private handleConsumerLeft;
    private restartConnectionsWithNewStream;
    startCamera(constraints?: MediaStreamConstraints): Promise<MediaStream>;
    startScreenShare(): Promise<MediaStream>;
    stopStreaming(): Promise<void>;
    updateVideoConfig(config: VideoConfig): Promise<void>;
    sendEmergencyStop(reason?: string): Promise<void>;
    initiateWebRTCWithConsumer(consumerId: string): Promise<void>;
    private handleWebRTCAnswer;
    private handleWebRTCIce;
    protected handleRoleSpecificMessage(message: WebSocketMessage): void;
    private handleStatusUpdate;
    private handleStreamStats;
    private notifyStreamStarted;
    private notifyStreamStopped;
    /**
     * Create a room and automatically connect as producer
     */
    static createAndConnect(baseUrl: string, workspaceId?: string, roomId?: string, participantId?: string): Promise<VideoProducer>;
    /**
     * Get the current room ID (useful when auto-created)
     */
    get currentRoomId(): string | null;
}
