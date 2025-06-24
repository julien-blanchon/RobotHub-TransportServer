/**
 * Type definitions for LeRobot Arena Video Client
 * ✅ Fully synchronized with server-side models.py
 */

// ============= CORE TYPES =============

export type ParticipantRole = 'producer' | 'consumer';

export type MessageType = 
  | 'frame_update'
  | 'video_config_update'
  | 'stream_started'
  | 'stream_stopped'
  | 'recovery_triggered'
  | 'heartbeat'
  | 'heartbeat_ack'
  | 'emergency_stop'
  | 'joined'
  | 'error'
  | 'participant_joined'
  | 'participant_left'
  | 'webrtc_offer'
  | 'webrtc_answer'
  | 'webrtc_ice'
  | 'status_update'
  | 'stream_stats';

// ============= VIDEO CONFIGURATION =============

export interface VideoConfig {
  encoding?: VideoEncoding;
  resolution?: Resolution;
  framerate?: number;
  bitrate?: number;
  quality?: number;
}

export interface Resolution {
  width: number;
  height: number;
}

export type VideoEncoding = 'jpeg' | 'h264' | 'vp8' | 'vp9';

export type RecoveryPolicy = 
  | 'freeze_last_frame'
  | 'connection_info' 
  | 'black_screen'
  | 'fade_to_black'
  | 'overlay_status';

export interface RecoveryConfig {
  frame_timeout_ms?: number;
  max_frame_reuse_count?: number;
  recovery_policy?: RecoveryPolicy;
  fallback_policy?: RecoveryPolicy;
  show_hold_indicators?: boolean;
  info_frame_bg_color?: [number, number, number];
  info_frame_text_color?: [number, number, number];
  fade_intensity?: number;
  overlay_opacity?: number;
}

// ============= DATA STRUCTURES =============

export interface FrameData {
  data: ArrayBuffer;
  metadata?: Record<string, unknown>;
}

export interface StreamStats {
  stream_id: string;
  duration_seconds: number;
  frame_count: number;
  total_bytes: number;
  average_fps: number;
  average_bitrate: number;
}

export interface ParticipantInfo {
  producer: string | null;
  consumers: string[];
  total: number;
}

export interface RoomInfo {
  id: string;
  workspace_id: string;
  participants: ParticipantInfo;
  frame_count: number;
  config: VideoConfig;
  has_producer: boolean;
  active_consumers: number;
}

export interface RoomState {
  room_id: string;
  workspace_id: string;
  participants: ParticipantInfo;
  frame_count: number;
  last_frame_time: string | null;
  current_config: VideoConfig;
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

export interface FrameUpdateMessage extends BaseMessage {
  type: 'frame_update';
  data: ArrayBuffer;
  metadata?: Record<string, unknown>;
}

export interface VideoConfigUpdateMessage extends BaseMessage {
  type: 'video_config_update';
  config: VideoConfig;
  source?: string;
}

export interface StreamStartedMessage extends BaseMessage {
  type: 'stream_started';
  config: VideoConfig;
  participant_id: string;
}

export interface StreamStoppedMessage extends BaseMessage {
  type: 'stream_stopped';
  participant_id: string;
  reason?: string;
}

export interface RecoveryTriggeredMessage extends BaseMessage {
  type: 'recovery_triggered';
  policy: RecoveryPolicy;
  reason: string;
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
  code?: string;
}

export interface ParticipantJoinedMessage extends BaseMessage {
  type: 'participant_joined';
  room_id: string;
  participant_id: string;
  role: ParticipantRole;
}

export interface ParticipantLeftMessage extends BaseMessage {
  type: 'participant_left';
  room_id: string;
  participant_id: string;
  role: ParticipantRole;
}

export interface WebRTCOfferMessage extends BaseMessage {
  type: 'webrtc_offer';
  offer: RTCSessionDescriptionInit;
  from_producer: string;
}

export interface WebRTCAnswerMessage extends BaseMessage {
  type: 'webrtc_answer';
  answer: RTCSessionDescriptionInit;
  from_consumer: string;
}

export interface WebRTCIceMessage extends BaseMessage {
  type: 'webrtc_ice';
  candidate: RTCIceCandidateInit;
  from_producer?: string;
  from_consumer?: string;
}

export interface StatusUpdateMessage extends BaseMessage {
  type: 'status_update';
  status: string;
  data?: Record<string, unknown>;
}

export interface StreamStatsMessage extends BaseMessage {
  type: 'stream_stats';
  stats: StreamStats;
}

export type WebSocketMessage = 
  | FrameUpdateMessage
  | VideoConfigUpdateMessage
  | StreamStartedMessage
  | StreamStoppedMessage
  | RecoveryTriggeredMessage
  | HeartbeatMessage
  | HeartbeatAckMessage
  | EmergencyStopMessage
  | JoinedMessage
  | ErrorMessage
  | ParticipantJoinedMessage
  | ParticipantLeftMessage
  | WebRTCOfferMessage
  | WebRTCAnswerMessage
  | WebRTCIceMessage
  | StatusUpdateMessage
  | StreamStatsMessage;

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

export interface WebRTCSignalResponse {
  success: boolean;
  workspace_id: string;
  response?: RTCSessionDescriptionInit | RTCIceCandidateInit;
  message?: string;
}

// ============= REQUEST TYPES =============

export interface CreateRoomRequest {
  room_id?: string;
  workspace_id?: string;
  name?: string;
  config?: VideoConfig;
  recovery_config?: RecoveryConfig;
  max_consumers?: number;
}

export interface WebRTCSignalRequest {
  client_id: string;
  message: RTCSessionDescriptionInit | RTCIceCandidateInit | Record<string, unknown>;
}

export interface JoinMessage {
  participant_id: string;
  role: ParticipantRole;
}

// ============= WEBRTC TYPES =============

export interface WebRTCConfig {
  iceServers?: RTCIceServer[];
  constraints?: MediaStreamConstraints;
  bitrate?: number;
  framerate?: number;
  resolution?: Resolution;
  codecPreferences?: string[];
}

export interface WebRTCStats {
  videoBitsPerSecond: number;
  framesPerSecond: number;
  frameWidth: number;
  frameHeight: number;
  packetsLost: number;
  totalPackets: number;
}

// ============= EVENT CALLBACK TYPES =============

export type FrameUpdateCallback = (frame: FrameData) => void;
export type VideoConfigUpdateCallback = (config: VideoConfig) => void;
export type StreamStartedCallback = (config: VideoConfig, participantId: string) => void;
export type StreamStoppedCallback = (participantId: string, reason?: string) => void;
export type RecoveryTriggeredCallback = (policy: RecoveryPolicy, reason: string) => void;
export type StatusUpdateCallback = (status: string, data?: Record<string, unknown>) => void;
export type StreamStatsCallback = (stats: StreamStats) => void;
export type ErrorCallback = (error: string) => void;
export type ConnectedCallback = () => void;
export type DisconnectedCallback = () => void;

// ============= CLIENT OPTIONS =============

export interface ClientOptions {
  base_url?: string;
  timeout?: number;
  reconnect_attempts?: number;
  heartbeat_interval?: number;
  webrtc_config?: WebRTCConfig;
} 