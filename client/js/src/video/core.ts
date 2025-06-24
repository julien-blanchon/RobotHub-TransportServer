/**
 * Core video client for LeRobot Arena
 * Base class providing REST API, WebSocket, and WebRTC functionality
 */

import { EventEmitter } from 'eventemitter3';
import type {
  ParticipantRole,
  RoomInfo,
  RoomState,
  ConnectionInfo,
  WebSocketMessage,
  JoinMessage,
  ListRoomsResponse,
  CreateRoomResponse,
  GetRoomResponse,
  GetRoomStateResponse,
  DeleteRoomResponse,
  WebRTCSignalResponse,
  WebRTCSignalRequest,
  ClientOptions,
  WebRTCConfig,
  WebRTCStats,
  VideoConfig,
  RecoveryConfig,
  ErrorCallback,
  ConnectedCallback,
  DisconnectedCallback,
} from './types.js';

export class VideoClientCore extends EventEmitter {
  protected baseUrl: string;
  protected apiBase: string;
  protected websocket: WebSocket | null = null;
  protected peerConnection: RTCPeerConnection | null = null;
  protected localStream: MediaStream | null = null;
  protected remoteStream: MediaStream | null = null;
  protected workspaceId: string | null = null;
  protected roomId: string | null = null;
  protected role: ParticipantRole | null = null;
  protected participantId: string | null = null;
  protected connected = false;
  protected options: ClientOptions;
  protected webrtcConfig: WebRTCConfig;

  // Event callbacks
  protected onErrorCallback: ErrorCallback | null = null;
  protected onConnectedCallback: ConnectedCallback | null = null;
  protected onDisconnectedCallback: DisconnectedCallback | null = null;

  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super();
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiBase = `${this.baseUrl}/video`;
    this.options = {
      timeout: 5000,
      reconnect_attempts: 3,
      heartbeat_interval: 30000,
      ...options,
    };
    this.webrtcConfig = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      constraints: { 
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30 }
        }, 
        audio: false 
      },
      bitrate: 1000000,
      framerate: 30,
      resolution: { width: 640, height: 480 },
      codecPreferences: ['VP8', 'H264'],
      ...this.options.webrtc_config,
    };
  }

  // ============= REST API METHODS =============

  async listRooms(workspaceId: string): Promise<RoomInfo[]> {
    const response = await this.fetchApi<ListRoomsResponse>(`/workspaces/${workspaceId}/rooms`);
    return response.rooms;
  }

  async createRoom(workspaceId?: string, roomId?: string, config?: VideoConfig, recoveryConfig?: RecoveryConfig): Promise<{ workspaceId: string; roomId: string }> {
    // Generate workspace ID if not provided
    const finalWorkspaceId = workspaceId || this.generateWorkspaceId();
    
    const payload = { 
      room_id: roomId, 
      workspace_id: finalWorkspaceId,
      config, 
      recovery_config: recoveryConfig 
    };
    const response = await this.fetchApi<CreateRoomResponse>(`/workspaces/${finalWorkspaceId}/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return { workspaceId: response.workspace_id, roomId: response.room_id };
  }

  async deleteRoom(workspaceId: string, roomId: string): Promise<boolean> {
    try {
      const response = await this.fetchApi<DeleteRoomResponse>(`/workspaces/${workspaceId}/rooms/${roomId}`, {
        method: 'DELETE',
      });
      return response.success;
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      throw error;
    }
  }

  async getRoomState(workspaceId: string, roomId: string): Promise<RoomState> {
    const response = await this.fetchApi<GetRoomStateResponse>(`/workspaces/${workspaceId}/rooms/${roomId}/state`);
    return response.state;
  }

  async getRoomInfo(workspaceId: string, roomId: string): Promise<RoomInfo> {
    const response = await this.fetchApi<GetRoomResponse>(`/workspaces/${workspaceId}/rooms/${roomId}`);
    return response.room;
  }

  // ============= WEBRTC SIGNALING =============

  async sendWebRTCSignal(workspaceId: string, roomId: string, clientId: string, message: RTCSessionDescriptionInit | RTCIceCandidateInit | Record<string, unknown>): Promise<WebRTCSignalResponse> {
    const request: WebRTCSignalRequest = { client_id: clientId, message };
    return this.fetchApi<WebRTCSignalResponse>(`/workspaces/${workspaceId}/rooms/${roomId}/webrtc/signal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  }

  // ============= WEBSOCKET CONNECTION =============

  async connectToRoom(
    workspaceId: string,
    roomId: string,
    role: ParticipantRole,
    participantId?: string
  ): Promise<boolean> {
    if (this.connected) {
      await this.disconnect();
    }

    this.workspaceId = workspaceId;
    this.roomId = roomId;
    this.role = role;
    this.participantId = participantId || `${role}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Convert HTTP URL to WebSocket URL
    const wsUrl = this.baseUrl
      .replace(/^http/, 'ws')
      .replace(/^https/, 'wss');
    const wsEndpoint = `${wsUrl}/video/workspaces/${workspaceId}/rooms/${roomId}/ws`;

    try {
      this.websocket = new WebSocket(wsEndpoint);

      // Set up WebSocket event handlers
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Connection timeout'));
        }, this.options.timeout || 5000);

        this.websocket!.onopen = () => {
          clearTimeout(timeout);
          this.sendJoinMessage();
        };

        this.websocket!.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);

            // Handle initial connection responses
            if (message.type === 'joined') {
              this.connected = true;
              this.onConnectedCallback?.();
              this.emit('connected');
              resolve(true);
            } else if (message.type === 'error') {
              this.handleError(message.message);
              resolve(false);
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.websocket!.onerror = (error) => {
          clearTimeout(timeout);
          console.error('WebSocket error:', error);
          this.handleError('WebSocket connection error');
          reject(error);
        };

        this.websocket!.onclose = () => {
          clearTimeout(timeout);
          this.connected = false;
          this.onDisconnectedCallback?.();
          this.emit('disconnected');
        };
      });
    } catch (error) {
      console.error('Failed to connect to room:', error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    // Close WebRTC connection
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    // Stop local streams
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
      this.localStream = null;
    }

    // Close WebSocket
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.close();
    }

    this.websocket = null;
    this.remoteStream = null;
    this.connected = false;
    this.workspaceId = null;
    this.roomId = null;
    this.role = null;
    this.participantId = null;

    this.onDisconnectedCallback?.();
    this.emit('disconnected');
  }

  // ============= WEBRTC METHODS =============

  createPeerConnection(): RTCPeerConnection {
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

    // ICE candidate handling
    this.peerConnection.onicecandidate = (event: RTCPeerConnectionIceEvent) => {
      if (event.candidate && this.workspaceId && this.roomId && this.participantId) {
        // Send ICE candidate via signaling
        this.sendWebRTCSignal(this.workspaceId, this.roomId, this.participantId, {
          type: 'ice',
          candidate: event.candidate.toJSON()
        } as Record<string, unknown>);
      }
    };

    // Handle remote stream
    this.peerConnection.ontrack = (event: RTCTrackEvent) => {
      console.info('📺 Received remote track:', event.track.kind);
      this.remoteStream = event.streams[0] || null;
      this.emit('remoteStream', this.remoteStream);
    };

    return this.peerConnection;
  }

  async createOffer(): Promise<RTCSessionDescriptionInit> {
    if (!this.peerConnection) {
      throw new Error('Peer connection not created');
    }

    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);
    
    return offer;
  }

  async createAnswer(offer: RTCSessionDescriptionInit): Promise<RTCSessionDescriptionInit> {
    if (!this.peerConnection) {
      throw new Error('Peer connection not created');
    }

    await this.peerConnection.setRemoteDescription(offer);
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);
    
    return answer;
  }

  async setRemoteDescription(description: RTCSessionDescriptionInit): Promise<void> {
    if (!this.peerConnection) {
      throw new Error('Peer connection not created');
    }

    await this.peerConnection.setRemoteDescription(description);
  }

  async addIceCandidate(candidate: RTCIceCandidateInit): Promise<void> {
    if (!this.peerConnection) {
      throw new Error('Peer connection not created');
    }

    await this.peerConnection.addIceCandidate(candidate);
  }

  // ============= MEDIA METHODS =============

  async startProducing(constraints?: MediaStreamConstraints): Promise<MediaStream> {
    const mediaConstraints = constraints || this.webrtcConfig.constraints;
    
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
      return this.localStream;
    } catch (error) {
      throw new Error(`Failed to start video production: ${error}`);
    }
  }

  async startScreenShare(): Promise<MediaStream> {
    try {
      this.localStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: this.webrtcConfig.resolution?.width || 1920,
          height: this.webrtcConfig.resolution?.height || 1080,
          frameRate: this.webrtcConfig.framerate || 30
        },
        audio: false
      });
      
      return this.localStream;
    } catch (error) {
      throw new Error(`Failed to start screen share: ${error}`);
    }
  }

  stopProducing(): void {
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
      this.localStream = null;
    }
  }

  // ============= GETTERS =============

  getLocalStream(): MediaStream | null {
    return this.localStream;
  }

  getRemoteStream(): MediaStream | null {
    return this.remoteStream;
  }

  getPeerConnection(): RTCPeerConnection | null {
    return this.peerConnection;
  }

  async getStats(): Promise<WebRTCStats | null> {
    if (!this.peerConnection) {
      return null;
    }

    const stats = await this.peerConnection.getStats();
    return this.extractVideoStats(stats);
  }

  // ============= MESSAGE HANDLING =============

  protected sendJoinMessage(): void {
    if (!this.websocket || !this.participantId || !this.role) return;

    const joinMessage: JoinMessage = {
      participant_id: this.participantId,
      role: this.role,
    };

    this.websocket.send(JSON.stringify(joinMessage));
  }

  protected handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'joined':
        console.log(`Successfully joined room ${message.room_id} as ${message.role}`);
        break;
      case 'heartbeat_ack':
        console.debug('Heartbeat acknowledged');
        break;
      case 'error':
        this.handleError(message.message);
        break;
      default:
        // Let subclasses handle specific message types
        this.handleRoleSpecificMessage(message);
    }
  }

  protected handleRoleSpecificMessage(message: WebSocketMessage): void {
    // To be overridden by subclasses
    this.emit('message', message);
  }

  protected handleError(errorMessage: string): void {
    console.error('Video client error:', errorMessage);
    this.onErrorCallback?.(errorMessage);
    this.emit('error', errorMessage);
  }

  // ============= UTILITY METHODS =============

  async sendHeartbeat(): Promise<void> {
    if (!this.connected || !this.websocket) return;

    const message = { type: 'heartbeat' as const };
    this.websocket.send(JSON.stringify(message));
  }

  isConnected(): boolean {
    return this.connected;
  }

  getConnectionInfo(): ConnectionInfo {
    return {
      connected: this.connected,
      workspace_id: this.workspaceId,
      room_id: this.roomId,
      role: this.role,
      participant_id: this.participantId,
      base_url: this.baseUrl,
    };
  }

  // ============= EVENT CALLBACK SETTERS =============

  onError(callback: ErrorCallback): void {
    this.onErrorCallback = callback;
  }

  onConnected(callback: ConnectedCallback): void {
    this.onConnectedCallback = callback;
  }

  onDisconnected(callback: DisconnectedCallback): void {
    this.onDisconnectedCallback = callback;
  }

  // ============= PRIVATE HELPERS =============

  private async fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.apiBase}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      signal: AbortSignal.timeout(this.options.timeout || 5000),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  private extractVideoStats(stats: RTCStatsReport): WebRTCStats | null {
    let inboundVideoStats: RTCInboundRtpStreamStats | null = null;
    let outboundVideoStats: RTCOutboundRtpStreamStats | null = null;

    stats.forEach((report) => {
      if (report.type === 'inbound-rtp' && 'kind' in report && report.kind === 'video') {
        inboundVideoStats = report as RTCInboundRtpStreamStats;
      } else if (report.type === 'outbound-rtp' && 'kind' in report && report.kind === 'video') {
        outboundVideoStats = report as RTCOutboundRtpStreamStats;
      }
    });

    // Handle inbound stats (consumer)
    if (inboundVideoStats) {
      return {
        videoBitsPerSecond: (inboundVideoStats as any).bytesReceived || 0,
        framesPerSecond: (inboundVideoStats as any).framesPerSecond || 0,
        frameWidth: (inboundVideoStats as any).frameWidth || 0,
        frameHeight: (inboundVideoStats as any).frameHeight || 0,
        packetsLost: (inboundVideoStats as any).packetsLost || 0,
        totalPackets: (inboundVideoStats as any).packetsReceived || (inboundVideoStats as any).framesDecoded || 0
      };
    }
    
    // Handle outbound stats (producer)
    if (outboundVideoStats) {
      return {
        videoBitsPerSecond: (outboundVideoStats as any).bytesSent || 0,
        framesPerSecond: (outboundVideoStats as any).framesPerSecond || 0,
        frameWidth: (outboundVideoStats as any).frameWidth || 0,
        frameHeight: (outboundVideoStats as any).frameHeight || 0,
        packetsLost: (outboundVideoStats as any).packetsLost || 0,
        totalPackets: (outboundVideoStats as any).packetsSent || (outboundVideoStats as any).framesSent || 0
      };
    }
    
    return null;
  }

  // ============= WORKSPACE HELPERS =============

  protected generateWorkspaceId(): string {
    // Generate a UUID-like workspace ID
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
} 