/**
 * Core robotics client for LeRobot Arena
 * Base class providing REST API and WebSocket functionality
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
  ClientOptions,
  ErrorCallback,
  ConnectedCallback,
  DisconnectedCallback,
} from './types.js';

export class RoboticsClientCore extends EventEmitter {
  protected baseUrl: string;
  protected apiBase: string;
  protected websocket: WebSocket | null = null;
  protected workspaceId: string | null = null;
  protected roomId: string | null = null;
  protected role: ParticipantRole | null = null;
  protected participantId: string | null = null;
  protected connected = false;
  protected options: ClientOptions;

  // Event callbacks
  protected onErrorCallback: ErrorCallback | null = null;
  protected onConnectedCallback: ConnectedCallback | null = null;
  protected onDisconnectedCallback: DisconnectedCallback | null = null;

  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super();
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiBase = `${this.baseUrl}/robotics`;
    this.options = {
      timeout: 5000,
      reconnect_attempts: 3,
      heartbeat_interval: 30000,
      ...options,
    };
  }

  // ============= REST API METHODS =============

  async listRooms(workspaceId: string): Promise<RoomInfo[]> {
    const response = await this.fetchApi<ListRoomsResponse>(`/workspaces/${workspaceId}/rooms`);
    return response.rooms;
  }

  async createRoom(workspaceId?: string, roomId?: string): Promise<{ workspaceId: string; roomId: string }> {
    // Generate workspace ID if not provided
    const finalWorkspaceId = workspaceId || this.generateWorkspaceId();
    
    const payload = roomId ? { room_id: roomId, workspace_id: finalWorkspaceId } : { workspace_id: finalWorkspaceId };
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
    const wsEndpoint = `${wsUrl}/robotics/workspaces/${workspaceId}/rooms/${roomId}/ws`;

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
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.close();
    }

    this.websocket = null;
    this.connected = false;
    this.workspaceId = null;
    this.roomId = null;
    this.role = null;
    this.participantId = null;

    this.onDisconnectedCallback?.();
    this.emit('disconnected');
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
    console.error('Client error:', errorMessage);
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