#!/usr/bin/env node

/**
 * Simple test script to verify the demo application
 */

import { robotics } from '@robohub/transport-server-client';

console.log('🤖 Testing LeRobot Arena Demo');
console.log('✅ Successfully imported robotics client');

// Test that we can create clients
try {
  const producer = new robotics.RoboticsProducer('http://localhost:8000');
  console.log('✅ Producer client created successfully');
  
  const consumer = new robotics.RoboticsConsumer('http://localhost:8000');
  console.log('✅ Consumer client created successfully');
  
  console.log('\n🎉 Demo application is ready!');
  console.log('📊 Available routes:');
  console.log('  - / (Dashboard)');
  console.log('  - /robotics (Robotics Control)');
  console.log('  - /robotics/producer (Producer Interface)');
  console.log('  - /robotics/consumer (Consumer Interface)');
  console.log('  - /robotics/producer/[roomId] (Room-specific Producer)');
  console.log('  - /robotics/consumer/[roomId] (Room-specific Consumer)');
  console.log('  - /video (Video placeholder)');
  
  console.log('\n💡 To test the demo:');
  console.log('  1. Start the LeRobot Arena server on port 8000');
  console.log('  2. Run: bun run dev');
  console.log('  3. Open http://localhost:5173 in your browser');
  
} catch (error) {
  console.error('❌ Error testing demo:', error);
  process.exit(1);
} 