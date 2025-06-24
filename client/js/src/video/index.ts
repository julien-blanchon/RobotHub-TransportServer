/**
 * LeRobot Arena Video Client - Main Module
 * 
 * TypeScript/JavaScript client for video streaming and monitoring
 */

// Export core classes
export { VideoClientCore } from './core.js';
export { VideoProducer } from './producer.js';
export { VideoConsumer } from './consumer.js';

// Export all types
export * from './types.js';

// Export factory functions for convenience
export { createProducerClient, createConsumerClient, createClient } from './factory.js';
