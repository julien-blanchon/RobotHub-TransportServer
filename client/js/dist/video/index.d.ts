/**
 * LeRobot Arena Video Client - Main Module
 *
 * TypeScript/JavaScript client for video streaming and monitoring
 */
export { VideoClientCore } from './core.js';
export { VideoProducer } from './producer.js';
export { VideoConsumer } from './consumer.js';
export * from './types.js';
export { createProducerClient, createConsumerClient, createClient } from './factory.js';
