/**
 * LeRobot Arena Robotics Client - Main Module
 * 
 * TypeScript/JavaScript client for robotics control and monitoring
 */

// Export core classes
export { RoboticsClientCore } from './core.js';
export { RoboticsProducer } from './producer.js';
export { RoboticsConsumer } from './consumer.js';

// Export all types
export * from './types.js';

// Export factory functions for convenience
export { createProducerClient, createConsumerClient, createClient } from './factory.js';
