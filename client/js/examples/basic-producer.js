#!/usr/bin/env node
/**
 * Basic Producer Example - LeRobot Arena
 * 
 * This example demonstrates:
 * - Creating a room
 * - Connecting as a producer
 * - Sending joint updates and state sync
 * - Basic error handling
 */

import { RoboticsProducer } from '../dist/robotics/index.js';

async function main() {
  console.log('🤖 LeRobot Arena Basic Producer Example 🤖');

  // Create producer client
  const producer = new RoboticsProducer('http://localhost:8000');

  // Set up event callbacks
  producer.onConnected(() => {
    console.log('✅ Producer connected!');
  });

  producer.onDisconnected(() => {
    console.log('👋 Producer disconnected!');
  });

  producer.onError((error) => {
    console.error('❌ Producer error:', error);
  });

  try {
    // Create a room
    console.log('\n📦 Creating room...');
    const roomId = await producer.createRoom();
    console.log(`✅ Room created: ${roomId}`);

    // Connect as producer
    console.log('\n🔌 Connecting as producer...');
    const success = await producer.connect(roomId, 'demo-producer');
    
    if (!success) {
      console.error('❌ Failed to connect as producer!');
      return;
    }

    console.log(`✅ Connected to room ${roomId} as producer`);

    // Show connection info
    const info = producer.getConnectionInfo();
    console.log('\n📊 Connection Info:');
    console.log(`  Room ID: ${info.room_id}`);
    console.log(`  Role: ${info.role}`);
    console.log(`  Participant ID: ${info.participant_id}`);

    // Send initial state sync
    console.log('\n📤 Sending initial state...');
    await producer.sendStateSync({
      base: 0.0,
      shoulder: 0.0,
      elbow: 0.0,
      wrist: 0.0,
      gripper: 0.0
    });
    console.log('✅ Initial state sent');

    // Simulate robot movement
    console.log('\n🤖 Simulating robot movement...');
    
    const movements = [
      { name: 'shoulder', value: 45.0, description: 'Raise shoulder' },
      { name: 'elbow', value: -30.0, description: 'Bend elbow' },
      { name: 'wrist', value: 15.0, description: 'Turn wrist' },
      { name: 'gripper', value: 0.5, description: 'Close gripper' },
    ];

    for (let i = 0; i < movements.length; i++) {
      const movement = movements[i];
      console.log(`  ${i + 1}. ${movement.description}: ${movement.value}°`);
      
      await producer.sendJointUpdate([{
        name: movement.name,
        value: movement.value
      }]);

      // Wait between movements
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // Send combined update
    console.log('\n📤 Sending combined update...');
    await producer.sendJointUpdate([
      { name: 'base', value: 90.0 },
      { name: 'shoulder', value: 60.0 },
      { name: 'elbow', value: -45.0 }
    ]);
    console.log('✅ Combined update sent');

    // Send heartbeat
    console.log('\n💓 Sending heartbeat...');
    await producer.sendHeartbeat();
    console.log('✅ Heartbeat sent');

    // Demonstrate emergency stop
    console.log('\n🚨 Testing emergency stop...');
    await producer.sendEmergencyStop('Demo emergency stop - testing safety');
    console.log('✅ Emergency stop sent');

    console.log('\n✅ Basic producer example completed!');
    console.log(`\n💡 Room ID: ${roomId}`);
    console.log('   You can use this room ID with the consumer example');

    // Keep running for a bit to allow consumers to connect
    console.log('\n⏳ Keeping producer alive for 30 seconds...');
    console.log('   (Consumers can connect during this time)');
    await new Promise(resolve => setTimeout(resolve, 30000));

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    // Always disconnect and cleanup
    if (producer.isConnected()) {
      console.log('\n🧹 Cleaning up...');
      await producer.disconnect();
      
      // Optionally delete the room
      const roomId = producer.currentRoomId;
      if (roomId) {
        await producer.deleteRoom(roomId);
        console.log(`🗑️  Deleted room ${roomId}`);
      }
    }
    console.log('👋 Goodbye!');
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n\n👋 Received SIGINT, shutting down gracefully...');
  process.exit(0);
});

main().catch(console.error); 