/**
 * Consumer client for receiving video streams in LeRobot Arena
 */

import { VideoClientCore } from './core.js';
import type {
  WebSocketMessage,
  FrameUpdateMessage,
  VideoConfigUpdateMessage,
  StreamStartedMessage,
  StreamStoppedMessage,
  RecoveryTriggeredMessage,
  StatusUpdateMessage,
  StreamStatsMessage,
  ClientOptions,
  WebRTCStats,
  FrameUpdateCallback,
  VideoConfigUpdateCallback,
  StreamStartedCallback,
  StreamStoppedCallback,
  RecoveryTriggeredCallback,
  StatusUpdateCallback,
  StreamStatsCallback,
  WebRTCOfferMessage,
  WebRTCIceMessage,
} from './types.js';

export class VideoConsumer extends VideoClientCore {
  // Event callbacks
  private onFrameUpdateCallback: FrameUpdateCallback | null = null;
  private onVideoConfigUpdateCallback: VideoConfigUpdateCallback | null = null;
  private onStreamStartedCallback: StreamStartedCallback | null = null;
  private onStreamStoppedCallback: StreamStoppedCallback | null = null;
  private onRecoveryTriggeredCallback: RecoveryTriggeredCallback | null = null;
  private onStatusUpdateCallback: StatusUpdateCallback | null = null;
  private onStreamStatsCallback: StreamStatsCallback | null = null;

  // ICE candidate queuing for proper timing
  private iceCandidateQueue: { candidate: RTCIceCandidate; fromProducer: string }[] = [];
  private hasRemoteDescription = false;

  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super(baseUrl, options);
  }

  // ============= CONSUMER CONNECTION =============

  async connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean> {
    const connected = await this.connectToRoom(workspaceId, roomId, 'consumer', participantId);
    
    if (connected) {
      // Create peer connection immediately so we're ready for WebRTC offers
      console.info('🔧 Creating peer connection for consumer...');
      await this.startReceiving();
    }
    
    return connected;
  }

  // ============= CONSUMER METHODS =============

  async startReceiving(): Promise<void> {
    if (!this.connected) {
      throw new Error('Must be connected to start receiving');
    }

    // Reset WebRTC state
    this.hasRemoteDescription = false;
    this.iceCandidateQueue = [];

    // Create peer connection for receiving
    this.createPeerConnection();
    
    // Set up to receive remote stream
    if (this.peerConnection) {
      this.peerConnection.ontrack = (event: RTCTrackEvent) => {
        console.info('📺 Received remote track:', event.track.kind);
        this.remoteStream = event.streams[0] || null;
        this.emit('remoteStream', this.remoteStream);
        this.emit('streamReceived', this.remoteStream);
      };
    }
  }

  async stopReceiving(): Promise<void> {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    this.remoteStream = null;
    this.emit('streamStopped');
  }

  // ============= WEBRTC NEGOTIATION =============

  async handleWebRTCOffer(message: WebRTCOfferMessage): Promise<void> {
    try {
      console.info(`📥 Received WebRTC offer from producer ${message.from_producer}`);
      
      if (!this.peerConnection) {
        console.warn('No peer connection available to handle offer');
        return;
      }

      // Reset state for new offer
      this.hasRemoteDescription = false;
      this.iceCandidateQueue = [];

      // Set remote description (the offer)
      await this.setRemoteDescription(message.offer);
      this.hasRemoteDescription = true;
      
      // Process any queued ICE candidates now that we have remote description
      await this.processQueuedIceCandidates();
      
      // Create answer
      const answer = await this.createAnswer(message.offer);
      
      console.info(`📤 Sending WebRTC answer to producer ${message.from_producer}`);
      
      // Send answer back through server to producer
      if (this.workspaceId && this.roomId && this.participantId) {
        await this.sendWebRTCSignal(this.workspaceId, this.roomId, this.participantId, {
          type: 'answer',
          sdp: answer.sdp,
          target_producer: message.from_producer,
        } as Record<string, unknown>);
      }
      
      console.info('✅ WebRTC negotiation completed from consumer side');
    } catch (error) {
      console.error('Failed to handle WebRTC offer:', error);
      this.handleError(`Failed to handle WebRTC offer: ${error}`);
    }
  }

  private async handleWebRTCIce(message: WebRTCIceMessage): Promise<void> {
    if (!this.peerConnection) {
      console.warn('No peer connection available to handle ICE');
      return;
    }

    try {
      console.info(`📥 Received WebRTC ICE from producer ${message.from_producer}`);
      
      const candidate = new RTCIceCandidate(message.candidate);
      
      if (!this.hasRemoteDescription) {
        // Queue ICE candidate until we have remote description
        console.info(`🔄 Queuing ICE candidate from ${message.from_producer} (no remote description yet)`);
        this.iceCandidateQueue.push({
          candidate,
          fromProducer: message.from_producer || 'unknown'
        });
        return;
      }
      
      // Add ICE candidate to peer connection
      await this.peerConnection.addIceCandidate(candidate);
      
      console.info(`✅ WebRTC ICE handled from producer ${message.from_producer}`);
    } catch (error) {
      console.error(`Failed to handle WebRTC ICE from ${message.from_producer}:`, error);
      this.handleError(`Failed to handle WebRTC ICE: ${error}`);
    }
  }

  private async processQueuedIceCandidates(): Promise<void> {
    if (this.iceCandidateQueue.length === 0) {
      return;
    }

    console.info(`🔄 Processing ${this.iceCandidateQueue.length} queued ICE candidates`);
    
    for (const { candidate, fromProducer } of this.iceCandidateQueue) {
      try {
        if (this.peerConnection) {
          await this.peerConnection.addIceCandidate(candidate);
          console.info(`✅ Processed queued ICE candidate from ${fromProducer}`);
        }
      } catch (error) {
        console.error(`Failed to process queued ICE candidate from ${fromProducer}:`, error);
      }
    }
    
    // Clear the queue
    this.iceCandidateQueue = [];
  }

  // Override to add producer targeting for ICE candidates
  override createPeerConnection(): RTCPeerConnection {
    const config: RTCConfiguration = {
      iceServers: this.webrtcConfig.iceServers || [
        { urls: 'stun:stun.l.google.com:19302' }
      ]
    };

    this.peerConnection = new RTCPeerConnection(config);

    // Connection state changes
    this.peerConnection.onconnectionstatechange = () => {
      const state = this.peerConnection?.connectionState;
      console.info(`🔌 WebRTC connection state: ${state}`);
    };

    // ICE connection state
    this.peerConnection.oniceconnectionstatechange = () => {
      const state = this.peerConnection?.iceConnectionState;
      console.info(`🧊 ICE connection state: ${state}`);
    };

    // ICE candidate handling - send to producer
    this.peerConnection.onicecandidate = (event: RTCPeerConnectionIceEvent) => {
      if (event.candidate && this.workspaceId && this.roomId && this.participantId) {
        // Send ICE candidate to producer
        this.sendIceCandidateToProducer(event.candidate);
      }
    };

    // Handle remote stream
    this.peerConnection.ontrack = (event: RTCTrackEvent) => {
      console.info('📺 Received remote track:', event.track.kind);
      this.remoteStream = event.streams[0] || null;
      this.emit('remoteStream', this.remoteStream);
      this.emit('streamReceived', this.remoteStream);
    };

    return this.peerConnection;
  }

  private async sendIceCandidateToProducer(candidate: RTCIceCandidate): Promise<void> {
    if (!this.workspaceId || !this.roomId || !this.participantId) return;

    try {
      // Get room info to find the producer
      const roomInfo = await this.getRoomInfo(this.workspaceId, this.roomId);
      
      if (roomInfo.participants.producer) {
        await this.sendWebRTCSignal(this.workspaceId, this.roomId, this.participantId, {
          type: 'ice',
          candidate: candidate.toJSON(),
          target_producer: roomInfo.participants.producer,
        } as Record<string, unknown>);
      }
    } catch (error) {
      console.error('Failed to send ICE candidate to producer:', error);
    }
  }

  private async handleStreamStarted(message: StreamStartedMessage): Promise<void> {
    if (this.onStreamStartedCallback) {
      this.onStreamStartedCallback(message.config, message.participant_id);
    }
    this.emit('streamStarted', message.config, message.participant_id);

    console.info(`🚀 Stream started by producer ${message.participant_id}, ready to receive video`);
  }

  // ============= EVENT CALLBACKS =============

  onFrameUpdate(callback: FrameUpdateCallback): void {
    this.onFrameUpdateCallback = callback;
  }

  onVideoConfigUpdate(callback: VideoConfigUpdateCallback): void {
    this.onVideoConfigUpdateCallback = callback;
  }

  onStreamStarted(callback: StreamStartedCallback): void {
    this.onStreamStartedCallback = callback;
  }

  onStreamStopped(callback: StreamStoppedCallback): void {
    this.onStreamStoppedCallback = callback;
  }

  onRecoveryTriggered(callback: RecoveryTriggeredCallback): void {
    this.onRecoveryTriggeredCallback = callback;
  }

  onStatusUpdate(callback: StatusUpdateCallback): void {
    this.onStatusUpdateCallback = callback;
  }

  onStreamStats(callback: StreamStatsCallback): void {
    this.onStreamStatsCallback = callback;
  }

  // ============= MESSAGE HANDLING =============

  protected override handleRoleSpecificMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'frame_update':
        this.handleFrameUpdate(message as FrameUpdateMessage);
        break;
      case 'video_config_update':
        this.handleVideoConfigUpdate(message as VideoConfigUpdateMessage);
        break;
      case 'stream_started':
        this.handleStreamStarted(message as StreamStartedMessage);
        break;
      case 'stream_stopped':
        this.handleStreamStopped(message as StreamStoppedMessage);
        break;
      case 'recovery_triggered':
        this.handleRecoveryTriggered(message as RecoveryTriggeredMessage);
        break;
      case 'status_update':
        this.handleStatusUpdate(message as StatusUpdateMessage);
        break;
      case 'stream_stats':
        this.handleStreamStats(message as StreamStatsMessage);
        break;
      case 'participant_joined':
        console.info(`📥 Participant joined: ${message.participant_id} as ${message.role}`);
        break;
      case 'participant_left':
        console.info(`📤 Participant left: ${message.participant_id} (${message.role})`);
        break;
      case 'webrtc_offer':
        this.handleWebRTCOffer(message as WebRTCOfferMessage);
        break;
      case 'webrtc_answer':
        console.info('📨 Received WebRTC answer (consumer should not receive this)');
        break;
      case 'webrtc_ice':
        this.handleWebRTCIce(message as WebRTCIceMessage);
        break;
      case 'emergency_stop':
        console.warn(`🚨 Emergency stop: ${message.reason || 'Unknown reason'}`);
        this.handleError(`Emergency stop: ${message.reason || 'Unknown reason'}`);
        break;
      case 'error':
        console.error(`Server error: ${message.message}`);
        this.handleError(message.message);
        break;
      default:
        console.warn(`Unknown message type for consumer: ${message.type}`);
    }
  }

  private handleFrameUpdate(message: FrameUpdateMessage): void {
    if (this.onFrameUpdateCallback) {
      const frameData = {
        data: message.data,
        metadata: message.metadata
      };
      this.onFrameUpdateCallback(frameData);
    }
    this.emit('frameUpdate', message.data);
  }

  private handleVideoConfigUpdate(message: VideoConfigUpdateMessage): void {
    if (this.onVideoConfigUpdateCallback) {
      this.onVideoConfigUpdateCallback(message.config);
    }
    this.emit('videoConfigUpdate', message.config);
  }

  private handleStreamStopped(message: StreamStoppedMessage): void {
    if (this.onStreamStoppedCallback) {
      this.onStreamStoppedCallback(message.participant_id, message.reason);
    }
    this.emit('streamStopped', message.participant_id, message.reason);
  }

  private handleRecoveryTriggered(message: RecoveryTriggeredMessage): void {
    if (this.onRecoveryTriggeredCallback) {
      this.onRecoveryTriggeredCallback(message.policy, message.reason);
    }
    this.emit('recoveryTriggered', message.policy, message.reason);
  }

  private handleStatusUpdate(message: StatusUpdateMessage): void {
    if (this.onStatusUpdateCallback) {
      this.onStatusUpdateCallback(message.status, message.data);
    }
    this.emit('statusUpdate', message.status, message.data);
  }

  private handleStreamStats(message: StreamStatsMessage): void {
    if (this.onStreamStatsCallback) {
      this.onStreamStatsCallback(message.stats);
    }
    this.emit('streamStats', message.stats);
  }

  // ============= UTILITY METHODS =============

  /**
   * Create a consumer and automatically connect to a room
   */
  static async createAndConnect(
    workspaceId: string,
    roomId: string,
    baseUrl = 'http://localhost:8000',
    participantId?: string
  ): Promise<VideoConsumer> {
    const consumer = new VideoConsumer(baseUrl);
    const connected = await consumer.connect(workspaceId, roomId, participantId);
    
    if (!connected) {
      throw new Error('Failed to connect as video consumer');
    }
    
    return consumer;
  }

  /**
   * Get the video element for displaying the remote stream
   */
  attachToVideoElement(videoElement: HTMLVideoElement): void {
    if (this.remoteStream) {
      videoElement.srcObject = this.remoteStream;
    }
    
    // Listen for future stream updates
    this.on('remoteStream', (stream: MediaStream) => {
      videoElement.srcObject = stream;
    });
  }

  /**
   * Get current video statistics
   */
  async getVideoStats(): Promise<WebRTCStats | null> {
    const stats = await this.getStats();
    return stats;
  }
} 