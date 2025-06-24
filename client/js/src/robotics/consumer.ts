/**
 * Consumer client for receiving robot commands in LeRobot Arena
 */

import { RoboticsClientCore } from './core.js';
import type {
  WebSocketMessage,
  JointUpdateMessage,
  StateSyncMessage,
  ClientOptions,
  JointUpdateCallback,
  StateSyncCallback,
} from './types.js';

export class RoboticsConsumer extends RoboticsClientCore {
  // Event callbacks
  private onStateSyncCallback: StateSyncCallback | null = null;
  private onJointUpdateCallback: JointUpdateCallback | null = null;

  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super(baseUrl, options);
  }

  // ============= CONSUMER CONNECTION =============

  async connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean> {
    return this.connectToRoom(workspaceId, roomId, 'consumer', participantId);
  }

  // ============= CONSUMER METHODS =============

  async getStateSyncAsync(): Promise<Record<string, number>> {
    if (!this.workspaceId || !this.roomId) {
      throw new Error('Must be connected to a room');
    }

    const state = await this.getRoomState(this.workspaceId, this.roomId);
    return state.joints;
  }

  // ============= EVENT CALLBACKS =============

  onStateSync(callback: StateSyncCallback): void {
    this.onStateSyncCallback = callback;
  }

  onJointUpdate(callback: JointUpdateCallback): void {
    this.onJointUpdateCallback = callback;
  }

  // ============= MESSAGE HANDLING =============

  protected override handleRoleSpecificMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'state_sync':
        this.handleStateSync(message as StateSyncMessage);
        break;
      case 'joint_update':
        this.handleJointUpdate(message as JointUpdateMessage);
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

  private handleStateSync(message: StateSyncMessage): void {
    if (this.onStateSyncCallback) {
      this.onStateSyncCallback(message.data);
    }
    this.emit('stateSync', message.data);
  }

  private handleJointUpdate(message: JointUpdateMessage): void {
    if (this.onJointUpdateCallback) {
      this.onJointUpdateCallback(message.data);
    }
    this.emit('jointUpdate', message.data);
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
  ): Promise<RoboticsConsumer> {
    const consumer = new RoboticsConsumer(baseUrl);
    const connected = await consumer.connect(workspaceId, roomId, participantId);
    
    if (!connected) {
      throw new Error('Failed to connect as consumer');
    }
    
    return consumer;
  }
} 