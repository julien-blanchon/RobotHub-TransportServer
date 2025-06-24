/**
 * Factory functions for creating LeRobot Arena robotics clients
 */

import { RoboticsProducer } from './producer.js';
import { RoboticsConsumer } from './consumer.js';
import type { ParticipantRole, ClientOptions } from './types.js';

/**
 * Factory function to create the appropriate client based on role
 */
export function createClient(
  role: ParticipantRole,
  baseUrl = 'http://localhost:8000',
  options: ClientOptions = {}
): RoboticsProducer | RoboticsConsumer {
  if (role === 'producer') {
    return new RoboticsProducer(baseUrl, options);
  }
  if (role === 'consumer') {
    return new RoboticsConsumer(baseUrl, options);
  }
  throw new Error(`Invalid role: ${role}. Must be 'producer' or 'consumer'`);
}

/**
 * Create and connect a producer client
 */
export async function createProducerClient(
  baseUrl = 'http://localhost:8000',
  workspaceId?: string,
  roomId?: string,
  participantId?: string,
  options: ClientOptions = {}
): Promise<RoboticsProducer> {
  const producer = new RoboticsProducer(baseUrl, options);

  const roomData = await producer.createRoom(workspaceId, roomId);
  const connected = await producer.connect(roomData.workspaceId, roomData.roomId, participantId);

  if (!connected) {
    throw new Error('Failed to connect as producer');
  }

  return producer;
}

/**
 * Create and connect a consumer client
 */
export async function createConsumerClient(
  workspaceId: string,
  roomId: string,
  baseUrl = 'http://localhost:8000',
  participantId?: string,
  options: ClientOptions = {}
): Promise<RoboticsConsumer> {
  const consumer = new RoboticsConsumer(baseUrl, options);
  const connected = await consumer.connect(workspaceId, roomId, participantId);

  if (!connected) {
    throw new Error('Failed to connect as consumer');
  }

  return consumer;
} 