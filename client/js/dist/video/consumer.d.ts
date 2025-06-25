/**
 * Consumer client for receiving video streams in RobotHub TransportServer
 */
import { VideoClientCore } from './core.js';
import type { WebSocketMessage, ClientOptions, WebRTCStats, FrameUpdateCallback, VideoConfigUpdateCallback, StreamStartedCallback, StreamStoppedCallback, RecoveryTriggeredCallback, StatusUpdateCallback, StreamStatsCallback, WebRTCOfferMessage } from './types.js';
export declare class VideoConsumer extends VideoClientCore {
    private onFrameUpdateCallback;
    private onVideoConfigUpdateCallback;
    private onStreamStartedCallback;
    private onStreamStoppedCallback;
    private onRecoveryTriggeredCallback;
    private onStatusUpdateCallback;
    private onStreamStatsCallback;
    private iceCandidateQueue;
    private hasRemoteDescription;
    constructor(baseUrl: string, options?: ClientOptions);
    connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean>;
    startReceiving(): Promise<void>;
    stopReceiving(): Promise<void>;
    handleWebRTCOffer(message: WebRTCOfferMessage): Promise<void>;
    private handleWebRTCIce;
    private processQueuedIceCandidates;
    createPeerConnection(): RTCPeerConnection;
    private sendIceCandidateToProducer;
    private handleStreamStarted;
    onFrameUpdate(callback: FrameUpdateCallback): void;
    onVideoConfigUpdate(callback: VideoConfigUpdateCallback): void;
    onStreamStarted(callback: StreamStartedCallback): void;
    onStreamStopped(callback: StreamStoppedCallback): void;
    onRecoveryTriggered(callback: RecoveryTriggeredCallback): void;
    onStatusUpdate(callback: StatusUpdateCallback): void;
    onStreamStats(callback: StreamStatsCallback): void;
    protected handleRoleSpecificMessage(message: WebSocketMessage): void;
    private handleFrameUpdate;
    private handleVideoConfigUpdate;
    private handleStreamStopped;
    private handleRecoveryTriggered;
    private handleStatusUpdate;
    private handleStreamStats;
    /**
     * Create a consumer and automatically connect to a room
     */
    static createAndConnect(workspaceId: string, roomId: string, baseUrl: string, participantId?: string): Promise<VideoConsumer>;
    /**
     * Get the video element for displaying the remote stream
     */
    attachToVideoElement(videoElement: HTMLVideoElement): void;
    /**
     * Get current video statistics
     */
    getVideoStats(): Promise<WebRTCStats | null>;
}
