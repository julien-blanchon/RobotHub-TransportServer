/**
 * Type definitions for LeRobot Arena Robotics Client
 */

// ============= CORE TYPES =============

export type ParticipantRole = 'producer' | 'consumer';

export type MessageType = 
  | 'joint_update'
  | 'state_sync' 
  | 'heartbeat'
  | 'heartbeat_ack'
  | 'emergency_stop'
  | 'joined'
  | 'error';

// ============= DATA STRUCTURES =============

export interface JointData {
  name: string;
  value: number;
  speed?: number;
}

export interface RoomInfo {
  id: string;
  workspace_id: string;
  participants: {
    producer: string | null;
    consumers: string[];
    total: number;
  };
  joints_count: number;
  has_producer?: boolean;
  active_consumers?: number;
}

export interface RoomState {
  room_id: string;
  workspace_id: string;
  joints: Record<string, number>;
  participants: {
    producer: string | null;
    consumers: string[];
    total: number;
  };
  timestamp: string;
}

export interface ConnectionInfo {
  connected: boolean;
  workspace_id: string | null;
  room_id: string | null;
  role: ParticipantRole | null;
  participant_id: string | null;
  base_url: string;
}

// ============= MESSAGE TYPES =============

export interface BaseMessage {
  type: MessageType;
  timestamp?: string;
}

export interface JointUpdateMessage extends BaseMessage {
  type: 'joint_update';
  data: JointData[];
  source?: string;
}

export interface StateSyncMessage extends BaseMessage {
  type: 'state_sync';
  data: Record<string, number>;
}

export interface HeartbeatMessage extends BaseMessage {
  type: 'heartbeat';
}

export interface HeartbeatAckMessage extends BaseMessage {
  type: 'heartbeat_ack';
}

export interface EmergencyStopMessage extends BaseMessage {
  type: 'emergency_stop';
  reason: string;
  source?: string;
}

export interface JoinedMessage extends BaseMessage {
  type: 'joined';
  room_id: string;
  role: ParticipantRole;
}

export interface ErrorMessage extends BaseMessage {
  type: 'error';
  message: string;
}

export type WebSocketMessage = 
  | JointUpdateMessage
  | StateSyncMessage
  | HeartbeatMessage
  | HeartbeatAckMessage
  | EmergencyStopMessage
  | JoinedMessage
  | ErrorMessage;

// ============= API RESPONSE TYPES =============

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ListRoomsResponse {
  success: boolean;
  workspace_id: string;
  rooms: RoomInfo[];
  total: number;
}

export interface CreateRoomResponse {
  success: boolean;
  workspace_id: string;
  room_id: string;
  message: string;
}

export interface GetRoomResponse {
  success: boolean;
  workspace_id: string;
  room: RoomInfo;
}

export interface GetRoomStateResponse {
  success: boolean;
  workspace_id: string;
  state: RoomState;
}

export interface DeleteRoomResponse {
  success: boolean;
  workspace_id: string;
  message: string;
}

// ============= REQUEST TYPES =============

export interface CreateRoomRequest {
  room_id?: string;
  workspace_id?: string;  // Optional - will be generated if not provided
}

export interface JoinMessage {
  participant_id: string;
  role: ParticipantRole;
}

// ============= EVENT CALLBACK TYPES =============

export type JointUpdateCallback = (joints: JointData[]) => void;
export type StateSyncCallback = (state: Record<string, number>) => void;
export type ErrorCallback = (error: string) => void;
export type ConnectedCallback = () => void;
export type DisconnectedCallback = () => void;

// ============= CLIENT OPTIONS =============

export interface ClientOptions {
  base_url?: string;
  timeout?: number;
  reconnect_attempts?: number;
  heartbeat_interval?: number;
} 