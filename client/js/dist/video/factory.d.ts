/**
 * Factory functions for creating RobotHub TransportServer video clients
 */
import { VideoProducer } from './producer.js';
import { VideoConsumer } from './consumer.js';
import type { ParticipantRole, ClientOptions } from './types.js';
/**
 * Factory function to create the appropriate client based on role
 */
export declare function createClient(role: ParticipantRole, baseUrl?: string, options?: ClientOptions): VideoProducer | VideoConsumer;
/**
 * Create and connect a producer client
 */
export declare function createProducerClient(baseUrl?: string, workspaceId?: string, roomId?: string, participantId?: string, options?: ClientOptions): Promise<VideoProducer>;
/**
 * Create and connect a consumer client
 */
export declare function createConsumerClient(workspaceId: string, roomId: string, baseUrl?: string, participantId?: string, options?: ClientOptions): Promise<VideoConsumer>;
