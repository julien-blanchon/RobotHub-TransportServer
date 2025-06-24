/**
 * Producer client for video streaming in LeRobot Arena
 */

import { VideoClientCore } from './core.js';
import type {
  WebSocketMessage,
  VideoConfigUpdateMessage,
  StreamStartedMessage,
  StreamStoppedMessage,
  StatusUpdateMessage,
  StreamStatsMessage,
  ClientOptions,
  VideoConfig,
  WebRTCAnswerMessage,
  WebRTCIceMessage,
} from './types.js';

export class VideoProducer extends VideoClientCore {
  // Multiple peer connections - one per consumer
  private consumerConnections: Map<string, RTCPeerConnection> = new Map();

  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super(baseUrl, options);
  }

  // ============= PRODUCER CONNECTION =============

  async connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean> {
    const success = await this.connectToRoom(workspaceId, roomId, 'producer', participantId);
    
    if (success) {
      // Listen for consumer join events to initiate WebRTC
      this.on('consumer_joined', (consumerId: string) => {
        console.info(`🎯 Consumer ${consumerId} joined, initiating WebRTC...`);
        this.initiateWebRTCWithConsumer(consumerId);
      });

      // Also check for existing consumers and initiate connections after a delay
      setTimeout(() => this.connectToExistingConsumers(), 1000);
    }
    
    return success;
  }

  private async connectToExistingConsumers(): Promise<void> {
    if (!this.workspaceId || !this.roomId) return;
    
    try {
      const roomInfo = await this.getRoomInfo(this.workspaceId, this.roomId);
      for (const consumerId of roomInfo.participants.consumers) {
        if (!this.consumerConnections.has(consumerId)) {
          console.info(`🔄 Connecting to existing consumer ${consumerId}`);
          await this.initiateWebRTCWithConsumer(consumerId);
        }
      }
    } catch (error) {
      console.error('Failed to connect to existing consumers:', error);
    }
  }

  private createPeerConnectionForConsumer(consumerId: string): RTCPeerConnection {
    const config: RTCConfiguration = {
      iceServers: this.webrtcConfig.iceServers || [
        { urls: 'stun:stun.l.google.com:19302' }
      ]
    };

    const peerConnection = new RTCPeerConnection(config);

    // Add local stream tracks to this connection
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, this.localStream!);
      });
    }

    // Connection state changes
    peerConnection.onconnectionstatechange = () => {
      const state = peerConnection.connectionState;
      console.info(`🔌 WebRTC connection state for ${consumerId}: ${state}`);
      
      if (state === 'failed' || state === 'disconnected') {
        console.warn(`Connection to ${consumerId} failed, attempting restart...`);
        setTimeout(() => this.restartConnectionToConsumer(consumerId), 2000);
      }
    };

    // ICE connection state
    peerConnection.oniceconnectionstatechange = () => {
      const state = peerConnection.iceConnectionState;
      console.info(`🧊 ICE connection state for ${consumerId}: ${state}`);
    };

    // ICE candidate handling for this specific consumer
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && this.workspaceId && this.roomId && this.participantId) {
        this.sendWebRTCSignal(this.workspaceId, this.roomId, this.participantId, {
          type: 'ice',
          candidate: event.candidate.toJSON(),
          target_consumer: consumerId,
        } as Record<string, unknown>);
      }
    };

    // Store the connection
    this.consumerConnections.set(consumerId, peerConnection);
    
    return peerConnection;
  }

  private async restartConnectionToConsumer(consumerId: string): Promise<void> {
    console.info(`🔄 Restarting connection to consumer ${consumerId}`);
    await this.initiateWebRTCWithConsumer(consumerId);
  }

  private handleConsumerLeft(consumerId: string): void {
    const peerConnection = this.consumerConnections.get(consumerId);
    if (peerConnection) {
      peerConnection.close();
      this.consumerConnections.delete(consumerId);
      console.info(`🧹 Cleaned up peer connection for consumer ${consumerId}`);
    }
  }

  private async restartConnectionsWithNewStream(stream: MediaStream): Promise<void> {
    console.info('🔄 Restarting connections with new stream...');
    
    // Close all existing connections
    for (const [consumerId, peerConnection] of this.consumerConnections) {
      peerConnection.close();
      console.info(`🧹 Closed existing connection to consumer ${consumerId}`);
    }
    this.consumerConnections.clear();

    // Get current consumers and restart connections
    try {
      if (this.workspaceId && this.roomId) {
        const roomInfo = await this.getRoomInfo(this.workspaceId, this.roomId);
        for (const consumerId of roomInfo.participants.consumers) {
          console.info(`🔄 Creating new connection to consumer ${consumerId}...`);
          await this.initiateWebRTCWithConsumer(consumerId);
        }
      }
    } catch (error) {
      console.error('Failed to restart connections:', error);
    }
  }

  // ============= PRODUCER METHODS =============

  async startCamera(constraints?: MediaStreamConstraints): Promise<MediaStream> {
    if (!this.connected) {
      throw new Error('Must be connected to start camera');
    }

    const stream = await this.startProducing(constraints);
    
    // Store the stream and restart connections with new tracks
    this.localStream = stream;
    await this.restartConnectionsWithNewStream(stream);

    // Notify about stream start
    this.notifyStreamStarted(stream);
    
    return stream;
  }

  override async startScreenShare(): Promise<MediaStream> {
    if (!this.connected) {
      throw new Error('Must be connected to start screen share');
    }

    const stream = await super.startScreenShare();
    
    // Store the stream and restart connections with new tracks
    this.localStream = stream;
    await this.restartConnectionsWithNewStream(stream);

    // Notify about stream start
    this.notifyStreamStarted(stream);
    
    return stream;
  }

  async stopStreaming(): Promise<void> {
    if (!this.connected || !this.websocket) {
      throw new Error('Must be connected to stop streaming');
    }

    // Close all consumer connections
    for (const [consumerId, peerConnection] of this.consumerConnections) {
      peerConnection.close();
      console.info(`🧹 Closed connection to consumer ${consumerId}`);
    }
    this.consumerConnections.clear();

    // Stop local stream
    this.stopProducing();

    // Notify about stream stop
    this.notifyStreamStopped();
  }

  async updateVideoConfig(config: VideoConfig): Promise<void> {
    if (!this.connected || !this.websocket) {
      throw new Error('Must be connected to update video config');
    }

    const message: VideoConfigUpdateMessage = {
      type: 'video_config_update',
      config,
      timestamp: new Date().toISOString(),
    };

    this.websocket.send(JSON.stringify(message));
  }

  async sendEmergencyStop(reason = 'Emergency stop'): Promise<void> {
    if (!this.connected || !this.websocket) {
      throw new Error('Must be connected to send emergency stop');
    }

    const message = {
      type: 'emergency_stop' as const,
      reason,
      timestamp: new Date().toISOString(),
    };

    this.websocket.send(JSON.stringify(message));
  }

  // ============= WEBRTC NEGOTIATION =============

  async initiateWebRTCWithConsumer(consumerId: string): Promise<void> {
    if (!this.workspaceId || !this.roomId || !this.participantId) {
      console.warn('WebRTC not ready, skipping negotiation with consumer');
      return;
    }

    // Clean up existing connection if any
    if (this.consumerConnections.has(consumerId)) {
      const existingConn = this.consumerConnections.get(consumerId);
      existingConn?.close();
      this.consumerConnections.delete(consumerId);
    }

    try {
      console.info(`🔄 Creating WebRTC offer for consumer ${consumerId}...`);
      
      // Create a new peer connection specifically for this consumer
      const peerConnection = this.createPeerConnectionForConsumer(consumerId);
      
      // Create offer with this consumer's peer connection
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      
      console.info(`📤 Sending WebRTC offer to consumer ${consumerId}...`);
      
      // Send offer to server/consumer
      await this.sendWebRTCSignal(this.workspaceId, this.roomId, this.participantId, {
        type: 'offer',
        sdp: offer.sdp,
        target_consumer: consumerId,
      } as Record<string, unknown>);
      
      console.info(`✅ WebRTC offer sent to consumer ${consumerId}`);
    } catch (error) {
      console.error(`Failed to initiate WebRTC with consumer ${consumerId}:`, error);
    }
  }

  private async handleWebRTCAnswer(message: WebRTCAnswerMessage): Promise<void> {
    try {
      const consumerId = message.from_consumer;
      console.info(`📥 Received WebRTC answer from consumer ${consumerId}`);
      
      const peerConnection = this.consumerConnections.get(consumerId);
      if (!peerConnection) {
        console.warn(`No peer connection found for consumer ${consumerId}`);
        return;
      }

      // Set remote description on the correct peer connection
      const answer = new RTCSessionDescription({
        type: 'answer',
        sdp: message.answer.sdp
      });
      
      await peerConnection.setRemoteDescription(answer);
      
      console.info(`✅ WebRTC negotiation completed with consumer ${consumerId}`);
    } catch (error) {
      console.error(`Failed to handle WebRTC answer from ${message.from_consumer}:`, error);
      this.handleError(`Failed to handle WebRTC answer: ${error}`);
    }
  }

  private async handleWebRTCIce(message: WebRTCIceMessage): Promise<void> {
    try {
      const consumerId = message.from_consumer;
      if (!consumerId) {
        console.warn('No consumer ID in ICE message');
        return;
      }

      const peerConnection = this.consumerConnections.get(consumerId);
      if (!peerConnection) {
        console.warn(`No peer connection found for consumer ${consumerId}`);
        return;
      }

      console.info(`📥 Received WebRTC ICE from consumer ${consumerId}`);
      
      // Add ICE candidate to the correct peer connection
      const candidate = new RTCIceCandidate(message.candidate);
      await peerConnection.addIceCandidate(candidate);
      
      console.info(`✅ WebRTC ICE handled with consumer ${consumerId}`);
    } catch (error) {
      console.error(`Failed to handle WebRTC ICE from ${message.from_consumer}:`, error);
      this.handleError(`Failed to handle WebRTC ICE: ${error}`);
    }
  }

  // ============= MESSAGE HANDLING =============

  protected override handleRoleSpecificMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'participant_joined':
        // Check if this is a consumer joining
        if (message.role === 'consumer' && message.participant_id !== this.participantId) {
          console.info(`🎯 Consumer ${message.participant_id} joined room`);
          this.emit('consumer_joined', message.participant_id);
        }
        break;
      case 'participant_left':
        // Check if this is a consumer leaving
        if (message.role === 'consumer') {
          console.info(`👋 Consumer ${message.participant_id} left room`);
          this.handleConsumerLeft(message.participant_id);
        }
        break;
      case 'webrtc_answer':
        this.handleWebRTCAnswer(message as WebRTCAnswerMessage);
        break;
      case 'webrtc_ice':
        this.handleWebRTCIce(message as WebRTCIceMessage);
        break;
      case 'status_update':
        this.handleStatusUpdate(message as StatusUpdateMessage);
        break;
      case 'stream_stats':
        this.handleStreamStats(message as StreamStatsMessage);
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
        console.warn(`Unknown message type for producer: ${message.type}`);
    }
  }

  private handleStatusUpdate(message: StatusUpdateMessage): void {
    console.info(`📊 Status update: ${message.status}`, message.data);
    this.emit('statusUpdate', message.status, message.data);
  }

  private handleStreamStats(message: StreamStatsMessage): void {
    console.debug(`📈 Stream stats:`, message.stats);
    this.emit('streamStats', message.stats);
  }

  // ============= UTILITY METHODS =============

  private async notifyStreamStarted(stream: MediaStream): Promise<void> {
    if (!this.websocket) return;

    const message: StreamStartedMessage = {
      type: 'stream_started',
      config: {
        resolution: this.webrtcConfig.resolution,
        framerate: this.webrtcConfig.framerate,
        bitrate: this.webrtcConfig.bitrate,
      },
      participant_id: this.participantId!,
      timestamp: new Date().toISOString(),
    };

    this.websocket.send(JSON.stringify(message));
    this.emit('streamStarted', stream);
  }

  private async notifyStreamStopped(): Promise<void> {
    if (!this.websocket) return;

    const message: StreamStoppedMessage = {
      type: 'stream_stopped',
      participant_id: this.participantId!,
      timestamp: new Date().toISOString(),
    };

    this.websocket.send(JSON.stringify(message));
    this.emit('streamStopped');
  }

  /**
   * Create a room and automatically connect as producer
   */
  static async createAndConnect(
    baseUrl = 'http://localhost:8000',
    workspaceId?: string,
    roomId?: string,
    participantId?: string
  ): Promise<VideoProducer> {
    const producer = new VideoProducer(baseUrl);
    
    const roomData = await producer.createRoom(workspaceId, roomId);
    const connected = await producer.connect(roomData.workspaceId, roomData.roomId, participantId);
    
    if (!connected) {
      throw new Error('Failed to connect as video producer');
    }
    
    return producer;
  }

  /**
   * Get the current room ID (useful when auto-created)
   */
  get currentRoomId(): string | null {
    return this.roomId;
  }
} 