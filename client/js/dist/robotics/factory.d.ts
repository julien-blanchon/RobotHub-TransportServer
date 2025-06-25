/**
 * Factory functions for creating RobotHub TransportServer robotics clients
 */
import { RoboticsProducer } from './producer.js';
import { RoboticsConsumer } from './consumer.js';
import type { ParticipantRole, ClientOptions } from './types.js';
/**
 * Factory function to create the appropriate client based on role
 */
export declare function createClient(role: ParticipantRole, baseUrl: string, options?: ClientOptions): RoboticsProducer | RoboticsConsumer;
/**
 * Create and connect a producer client
 */
export declare function createProducerClient(baseUrl: string, workspaceId?: string, roomId?: string, participantId?: string, options?: ClientOptions): Promise<RoboticsProducer>;
/**
 * Create and connect a consumer client
 */
export declare function createConsumerClient(workspaceId: string, roomId: string, baseUrl: string, participantId?: string, options?: ClientOptions): Promise<RoboticsConsumer>;
