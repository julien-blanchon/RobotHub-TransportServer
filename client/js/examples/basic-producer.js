#!/usr/bin/env node
/**
 * Basic Producer Example - RobotHub TransportServer
 * 
 * This example demonstrates:
 * - Creating a room with workspace support
 * - Connecting as a producer with workspace_id and room_id
 * - Sending joint updates and state sync
 * - Modern error handling and cleanup
 * - Enhanced user feedback
 */

import { RoboticsProducer } from '../dist/robotics/index.js';

async function main() {
  console.log('🤖 RobotHub TransportServer Basic Producer Example 🤖');
  console.log('📋 This example will create a room and demonstrate producer functionality\n');

  // Create producer client
  const producer = new RoboticsProducer('http://localhost:8000');

  // Track connection state
  let isConnected = false;
  let workspaceId = null;
  let roomId = null;

  // Set up event callbacks with enhanced feedback
  producer.onConnected(() => {
    isConnected = true;
    console.log('✅ Producer connected successfully!');
  });

  producer.onDisconnected(() => {
    isConnected = false;
    console.log('👋 Producer disconnected');
  });

  producer.onError((error) => {
    console.error('❌ Producer error:', error);
  });

  try {
    // Create a room (returns both workspace_id and room_id)
    console.log('📦 Creating new room...');
    const roomInfo = await producer.createRoom();
    workspaceId = roomInfo.workspaceId;
    roomId = roomInfo.roomId;
    
    console.log(`✅ Room created successfully!`);
    console.log(`   Workspace ID: ${workspaceId}`);
    console.log(`   Room ID: ${roomId}`);

    // Connect as producer with both workspace_id and room_id
    console.log('\n🔌 Connecting as producer...');
    const success = await producer.connect(workspaceId, roomId, 'demo-producer');
    
    if (!success) {
      console.error('❌ Failed to connect as producer!');
      console.log('💡 Make sure the server is running on http://localhost:8000');
      return;
    }

    console.log(`✅ Connected to room successfully!`);

    // Show detailed connection info
    const info = producer.getConnectionInfo();
    console.log('\n📊 Connection Details:');
    console.log(`   Workspace ID: ${info.workspace_id}`);
    console.log(`   Room ID: ${info.room_id}`);
    console.log(`   Role: ${info.role}`);
    console.log(`   Participant ID: ${info.participant_id}`);
    console.log(`   Server URL: ${info.base_url}`);

    // Send initial state sync with enhanced feedback
    console.log('\n📤 Sending initial robot state...');
    const initialState = {
      base: 0.0,
      shoulder: 0.0,
      elbow: 0.0,
      wrist: 0.0,
      gripper: 0.0
    };
    
    await producer.sendStateSync(initialState);
    console.log('✅ Initial state sent:');
    Object.entries(initialState).forEach(([joint, value]) => {
      console.log(`   ${joint}: ${value}°`);
    });

    // Simulate realistic robot movement sequence
    console.log('\n🤖 Simulating robot movement sequence...');
    
    const movements = [
      { 
        joints: [{ name: 'base', value: 30.0 }], 
        description: 'Rotate base to 30°',
        delay: 1500 
      },
      { 
        joints: [{ name: 'shoulder', value: 45.0 }], 
        description: 'Raise shoulder to 45°',
        delay: 1200 
      },
      { 
        joints: [{ name: 'elbow', value: -30.0 }], 
        description: 'Bend elbow to -30°',
        delay: 1000 
      },
      { 
        joints: [{ name: 'wrist', value: 15.0 }], 
        description: 'Turn wrist to 15°',
        delay: 800 
      },
      { 
        joints: [{ name: 'gripper', value: 0.8 }], 
        description: 'Close gripper to 80%',
        delay: 600 
      },
    ];

    for (let i = 0; i < movements.length; i++) {
      const movement = movements[i];
      console.log(`\n   Step ${i + 1}: ${movement.description}`);
      
      await producer.sendJointUpdate(movement.joints);
      console.log(`   ✅ Joint update sent: ${movement.joints.map(j => `${j.name}=${j.value}°`).join(', ')}`);

      // Wait between movements for realistic timing
      console.log(`   ⏳ Waiting ${movement.delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, movement.delay));
    }

    // Send combined multi-joint update
    console.log('\n📤 Sending combined multi-joint update...');
    const combinedUpdate = [
      { name: 'base', value: 90.0 },
      { name: 'shoulder', value: 60.0 },
      { name: 'elbow', value: -45.0 }
    ];
    
    await producer.sendJointUpdate(combinedUpdate);
    console.log('✅ Combined update sent:');
    combinedUpdate.forEach(joint => {
      console.log(`   ${joint.name}: ${joint.value}°`);
    });

    // Send final state sync
    console.log('\n📤 Sending final state synchronization...');
    const finalState = {
      base: 90.0,
      shoulder: 60.0,
      elbow: -45.0,
      wrist: 15.0,
      gripper: 0.8
    };
    
    await producer.sendStateSync(finalState);
    console.log('✅ Final state synchronized');

    // Send heartbeat to verify connection
    console.log('\n💓 Sending heartbeat...');
    await producer.sendHeartbeat();
    console.log('✅ Heartbeat sent - connection healthy');

    // Demonstrate emergency stop
    console.log('\n🚨 Testing emergency stop functionality...');
    await producer.sendEmergencyStop('Demo emergency stop - testing safety protocols');
    console.log('✅ Emergency stop sent successfully');

    console.log('\n🎉 Basic producer example completed successfully!');
    
    // Display connection info for consumers
    console.log('\n📋 Connection Information for Consumers:');
    console.log(`   Workspace ID: ${workspaceId}`);
    console.log(`   Room ID: ${roomId}`);
    console.log('\n💡 You can use these IDs with the consumer example to connect to this room');

    // Keep running to allow consumers to connect
    console.log('\n⏳ Keeping producer alive for 30 seconds...');
    console.log('   (Consumers can connect during this time using the IDs above)');
    
    const keepAliveStart = Date.now();
    const keepAliveDuration = 30000;
    
    // Show countdown
    const countdownInterval = setInterval(() => {
      const elapsed = Date.now() - keepAliveStart;
      const remaining = Math.max(0, keepAliveDuration - elapsed);
      
      if (remaining > 0) {
        process.stdout.write(`\r   Time remaining: ${Math.ceil(remaining / 1000)}s `);
      } else {
        process.stdout.write('\r   Time is up!                    \n');
        clearInterval(countdownInterval);
      }
    }, 1000);
    
    await new Promise(resolve => setTimeout(resolve, keepAliveDuration));
    clearInterval(countdownInterval);

  } catch (error) {
    console.error('\n❌ Error occurred:', error.message);
    if (error.stack) {
      console.error('Stack trace:', error.stack);
    }
  } finally {
    // Always disconnect and cleanup
    console.log('\n🧹 Cleaning up resources...');
    
    if (producer.isConnected()) {
      console.log('   Disconnecting from room...');
      await producer.disconnect();
      console.log('   ✅ Disconnected successfully');
    }
    
    // Delete the room to clean up server resources
    if (workspaceId && roomId) {
      try {
        console.log('   Deleting room...');
        const deleted = await producer.deleteRoom(workspaceId, roomId);
        if (deleted) {
          console.log(`   ✅ Room deleted: ${roomId}`);
        } else {
          console.log(`   ⚠️  Room may have already been deleted: ${roomId}`);
        }
      } catch (error) {
        console.log(`   ⚠️  Could not delete room: ${error.message}`);
      }
    }
    
    console.log('\n👋 Producer example finished. Goodbye!');
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', async () => {
  console.log('\n\n🛑 Received interrupt signal (Ctrl+C)');
  console.log('🧹 Shutting down gracefully...');
  process.exit(0);
});

// Handle uncaught errors
process.on('unhandledRejection', (error) => {
  console.error('\n❌ Unhandled promise rejection:', error);
  process.exit(1);
});

main().catch((error) => {
  console.error('\n💥 Fatal error:', error);
  process.exit(1);
}); 