#!/usr/bin/env node
/**
 * Basic Consumer Example - LeRobot Arena
 * 
 * This example demonstrates:
 * - Connecting to an existing room as a consumer
 * - Receiving joint updates and state sync
 * - Setting up callbacks
 * - Getting current state
 */

import { RoboticsConsumer } from '../dist/robotics/index.js';
import { createInterface } from 'readline';

async function main() {
  console.log('🤖 LeRobot Arena Basic Consumer Example 🤖');

  // Get room ID from user
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const roomId = await new Promise((resolve) => {
    rl.question('Enter room ID to connect to: ', (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });

  if (!roomId) {
    console.error('❌ Room ID is required!');
    return;
  }

  // Create consumer client
  const consumer = new RoboticsConsumer('http://localhost:8000');

  // Track received updates
  let updateCount = 0;
  let stateCount = 0;
  const receivedUpdates = [];
  const receivedStates = [];

  // Set up callbacks
  consumer.onJointUpdate((joints) => {
    updateCount++;
    console.log(`📥 [${updateCount}] Joint update: ${joints.length} joints`);
    
    // Show joint details
    joints.forEach(joint => {
      console.log(`    ${joint.name}: ${joint.value}${joint.speed ? ` (speed: ${joint.speed})` : ''}`);
    });
    
    receivedUpdates.push(joints);
  });

  consumer.onStateSync((state) => {
    stateCount++;
    console.log(`📊 [${stateCount}] State sync: ${Object.keys(state).length} joints`);
    
    // Show state details
    Object.entries(state).forEach(([name, value]) => {
      console.log(`    ${name}: ${value}`);
    });
    
    receivedStates.push(state);
  });

  consumer.onError((errorMsg) => {
    console.error('❌ Consumer error:', errorMsg);
  });

  consumer.onConnected(() => {
    console.log('✅ Consumer connected!');
  });

  consumer.onDisconnected(() => {
    console.log('👋 Consumer disconnected!');
  });

  try {
    // Connect to the room
    console.log(`\n🔌 Connecting to room ${roomId}...`);
    const success = await consumer.connect(roomId, 'demo-consumer');
    
    if (!success) {
      console.error('❌ Failed to connect to room!');
      console.log('💡 Make sure the room exists and the server is running');
      return;
    }

    console.log(`✅ Connected to room ${roomId} as consumer`);

    // Show connection info
    const info = consumer.getConnectionInfo();
    console.log('\n📊 Connection Info:');
    console.log(`  Room ID: ${info.room_id}`);
    console.log(`  Role: ${info.role}`);
    console.log(`  Participant ID: ${info.participant_id}`);

    // Get initial state
    console.log('\n📋 Getting initial state...');
    const initialState = await consumer.getStateSyncAsync();
    console.log('Initial state:', Object.keys(initialState).length, 'joints');
    
    if (Object.keys(initialState).length > 0) {
      Object.entries(initialState).forEach(([name, value]) => {
        console.log(`  ${name}: ${value}`);
      });
    } else {
      console.log('  (Empty - no joints set yet)');
    }

    // Listen for updates
    console.log('\n👂 Listening for updates for 60 seconds...');
    console.log('   (Producer can send commands during this time)');
    
    const startTime = Date.now();
    const duration = 60000; // 60 seconds

    // Show periodic status
    const statusInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, duration - elapsed);
      
      if (remaining > 0) {
        console.log(`\n📊 Status (${Math.floor(remaining / 1000)}s remaining):`);
        console.log(`   Updates received: ${updateCount}`);
        console.log(`   State syncs received: ${stateCount}`);
      }
    }, 10000); // Every 10 seconds

    await new Promise(resolve => setTimeout(resolve, duration));
    clearInterval(statusInterval);

    // Show final summary
    console.log('\n📊 Final Summary:');
    console.log(`   Total updates received: ${updateCount}`);
    console.log(`   Total state syncs received: ${stateCount}`);
    
    // Get final state
    const finalState = await consumer.getStateSyncAsync();
    console.log('\n📋 Final state:');
    if (Object.keys(finalState).length > 0) {
      Object.entries(finalState).forEach(([name, value]) => {
        console.log(`  ${name}: ${value}`);
      });
    } else {
      console.log('  (Empty)');
    }

    console.log('\n✅ Basic consumer example completed!');

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    // Always disconnect
    if (consumer.isConnected()) {
      console.log('\n🧹 Disconnecting...');
      await consumer.disconnect();
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