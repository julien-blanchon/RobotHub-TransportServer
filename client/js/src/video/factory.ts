/**
 * Factory functions for creating LeRobot Arena video clients
 */

import { VideoProducer } from './producer.js';
import { VideoConsumer } from './consumer.js';
import type { ParticipantRole, ClientOptions } from './types.js';

/**
 * Factory function to create the appropriate client based on role
 */
export function createClient(
  role: ParticipantRole,
  baseUrl = 'http://localhost:8000',
  options: ClientOptions = {}
): VideoProducer | VideoConsumer {
  if (role === 'producer') {
    return new VideoProducer(baseUrl, options);
  }
  if (role === 'consumer') {
    return new VideoConsumer(baseUrl, options);
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
): Promise<VideoProducer> {
  const producer = new VideoProducer(baseUrl, options);

  const roomData = await producer.createRoom(workspaceId, roomId);
  const connected = await producer.connect(roomData.workspaceId, roomData.roomId, participantId);

  if (!connected) {
    throw new Error('Failed to connect as video producer');
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
): Promise<VideoConsumer> {
  const consumer = new VideoConsumer(baseUrl, options);
  const connected = await consumer.connect(workspaceId, roomId, participantId);

  if (!connected) {
    throw new Error('Failed to connect as video consumer');
  }

  return consumer;
} 