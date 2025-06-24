/**
 * Producer client for controlling robots in LeRobot Arena
 */

import { RoboticsClientCore } from './core.js';
import type {
  JointData,
  WebSocketMessage,
  JointUpdateMessage,
  ClientOptions,
} from './types.js';

export class RoboticsProducer extends RoboticsClientCore {
  constructor(baseUrl = 'http://localhost:8000', options: ClientOptions = {}) {
    super(baseUrl, options);
  }

  // ============= PRODUCER CONNECTION =============

  async connect(workspaceId: string, roomId: string, participantId?: string): Promise<boolean> {
    return this.connectToRoom(workspaceId, roomId, 'producer', participantId);
  }

  // ============= PRODUCER METHODS =============

  async sendJointUpdate(joints: JointData[]): Promise<void> {
    if (!this.connected || !this.websocket) {
      throw new Error('Must be connected to send joint updates');
    }

    const message: JointUpdateMessage = {
      type: 'joint_update',
      data: joints,
      timestamp: new Date().toISOString(),
    };

    this.websocket.send(JSON.stringify(message));
  }

  async sendStateSync(state: Record<string, number>): Promise<void> {
    if (!this.connected || !this.websocket) {
      throw new Error('Must be connected to send state sync');
    }

    // Convert state object to joint updates format
    const joints: JointData[] = Object.entries(state).map(([name, value]) => ({
      name,
      value,
    }));

    await this.sendJointUpdate(joints);
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

  // ============= MESSAGE HANDLING =============

  protected override handleRoleSpecificMessage(message: WebSocketMessage): void {
    switch (message.type) {
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

  // ============= UTILITY METHODS =============

  /**
   * Create a room and automatically connect as producer
   */
  static async createAndConnect(
    baseUrl = 'http://localhost:8000',
    workspaceId?: string,
    roomId?: string,
    participantId?: string
  ): Promise<RoboticsProducer> {
    const producer = new RoboticsProducer(baseUrl);
    
    const roomData = await producer.createRoom(workspaceId, roomId);
    const connected = await producer.connect(roomData.workspaceId, roomData.roomId, participantId);
    
    if (!connected) {
      throw new Error('Failed to connect as producer');
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