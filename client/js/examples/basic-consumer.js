#!/usr/bin/env node
/**
 * Basic Consumer Example - RobotHub TransportServer
 * 
 * This example demonstrates:
 * - Connecting to an existing room as a consumer using workspace_id and room_id
 * - Receiving joint updates and state sync
 * - Setting up callbacks with enhanced feedback
 * - Getting current state and connection info
 * - Modern error handling and resource management
 */

import { RoboticsConsumer } from '../dist/robotics/index.js';
import { createInterface } from 'readline';

async function promptUser(question) {
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function main() {
  console.log('🤖 RobotHub TransportServer Basic Consumer Example 🤖');
  console.log('📋 This example will connect to an existing room and listen for updates\n');

  // Get connection details from user
  console.log('📝 Please provide the connection details:');
  
  const workspaceId = await promptUser('Enter workspace ID: ');
  if (!workspaceId) {
    console.error('❌ Workspace ID is required!');
    console.log('💡 You can get this from the producer example output');
    return;
  }

  const roomId = await promptUser('Enter room ID: ');
  if (!roomId) {
    console.error('❌ Room ID is required!');
    console.log('💡 You can get this from the producer example output');
    return;
  }

  console.log('\n✅ Connection details received:');
  console.log(`   Workspace ID: ${workspaceId}`);
  console.log(`   Room ID: ${roomId}`);

  // Create consumer client
  const consumer = new RoboticsConsumer('http://localhost:8000');

  // Track received data and connection state
  let updateCount = 0;
  let stateCount = 0;
  let isConnected = false;
  const receivedUpdates = [];
  const receivedStates = [];

  // Set up callbacks with enhanced feedback
  consumer.onJointUpdate((joints) => {
    updateCount++;
    console.log(`\n📥 [${updateCount}] Joint update received: ${joints.length} joint(s)`);
    
    // Show joint details with better formatting
    joints.forEach(joint => {
      const speedInfo = joint.speed ? ` (speed: ${joint.speed})` : '';
      console.log(`    🔧 ${joint.name}: ${joint.value}°${speedInfo}`);
    });
    
    receivedUpdates.push({ timestamp: new Date(), joints });
  });

  consumer.onStateSync((state) => {
    stateCount++;
    console.log(`\n📊 [${stateCount}] State sync received: ${Object.keys(state).length} joint(s)`);
    
    // Show state details with better formatting
    if (Object.keys(state).length > 0) {
      Object.entries(state).forEach(([name, value]) => {
        console.log(`    ⚙️  ${name}: ${value}°`);
      });
    } else {
      console.log('    (No joint data)');
    }
    
    receivedStates.push({ timestamp: new Date(), state });
  });

  consumer.onError((errorMsg) => {
    console.error('\n❌ Consumer error:', errorMsg);
  });

  consumer.onConnected(() => {
    isConnected = true;
    console.log('\n✅ Consumer connected successfully!');
  });

  consumer.onDisconnected(() => {
    isConnected = false;
    console.log('\n👋 Consumer disconnected');
  });

  try {
    // Connect to the room with workspace_id and room_id
    console.log(`\n🔌 Connecting to room...`);
    console.log(`   Workspace ID: ${workspaceId}`);
    console.log(`   Room ID: ${roomId}`);
    
    const success = await consumer.connect(workspaceId, roomId, 'demo-consumer');
    
    if (!success) {
      console.error('\n❌ Failed to connect to room!');
      console.log('💡 Possible reasons:');
      console.log('   - Room does not exist');
      console.log('   - Server is not running on http://localhost:8000');
      console.log('   - Incorrect workspace_id or room_id');
      console.log('   - Network connectivity issues');
      return;
    }

    console.log(`\n✅ Successfully connected to room!`);

    // Show detailed connection info
    const info = consumer.getConnectionInfo();
    console.log('\n📊 Connection Details:');
    console.log(`   Workspace ID: ${info.workspace_id}`);
    console.log(`   Room ID: ${info.room_id}`);
    console.log(`   Role: ${info.role}`);
    console.log(`   Participant ID: ${info.participant_id}`);
    console.log(`   Server URL: ${info.base_url}`);

    // Get initial state with enhanced feedback
    console.log('\n📋 Retrieving initial robot state...');
    try {
      const initialState = await consumer.getStateSyncAsync();
      console.log(`✅ Initial state retrieved: ${Object.keys(initialState).length} joint(s)`);
      
      if (Object.keys(initialState).length > 0) {
        console.log('   Current joint positions:');
        Object.entries(initialState).forEach(([name, value]) => {
          console.log(`    ⚙️  ${name}: ${value}°`);
        });
      } else {
        console.log('   📝 No joints configured yet (empty state)');
        console.log('   💡 Producer can send initial state to populate this');
      }
    } catch (error) {
      console.log(`⚠️  Could not retrieve initial state: ${error.message}`);
    }

    // Listen for updates with enhanced status reporting
    console.log('\n👂 Listening for real-time updates...');
    console.log('   Duration: 60 seconds');
    console.log('   💡 Run the producer example to send updates to this consumer');
    
    const startTime = Date.now();
    const duration = 60000; // 60 seconds

    // Show periodic status with detailed information
    const statusInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, duration - elapsed);
      
      if (remaining > 0) {
        console.log(`\n📊 Status Update (${Math.floor(remaining / 1000)}s remaining):`);
        console.log(`   Connection: ${isConnected ? '✅ Connected' : '❌ Disconnected'}`);
        console.log(`   Joint updates received: ${updateCount}`);
        console.log(`   State syncs received: ${stateCount}`);
        console.log(`   Total messages: ${updateCount + stateCount}`);
        
        if (receivedUpdates.length > 0) {
          const lastUpdate = receivedUpdates[receivedUpdates.length - 1];
          const timeSinceLastUpdate = Date.now() - lastUpdate.timestamp.getTime();
          console.log(`   Last update: ${Math.floor(timeSinceLastUpdate / 1000)}s ago`);
        }
      }
    }, 15000); // Every 15 seconds

    // Wait for the duration
    await new Promise(resolve => setTimeout(resolve, duration));
    clearInterval(statusInterval);

    // Show comprehensive final summary
    console.log('\n📊 Session Summary:');
    console.log(`   Duration: 60 seconds`);
    console.log(`   Total joint updates: ${updateCount}`);
    console.log(`   Total state syncs: ${stateCount}`);
    console.log(`   Total messages: ${updateCount + stateCount}`);
    
    if (updateCount > 0) {
      console.log(`   Average update rate: ${(updateCount / 60).toFixed(2)} updates/second`);
    }
    
    // Get final state for comparison
    console.log('\n📋 Retrieving final robot state...');
    try {
      const finalState = await consumer.getStateSyncAsync();
      console.log(`✅ Final state retrieved: ${Object.keys(finalState).length} joint(s)`);
      
      if (Object.keys(finalState).length > 0) {
        console.log('   Final joint positions:');
        Object.entries(finalState).forEach(([name, value]) => {
          console.log(`    ⚙️  ${name}: ${value}°`);
        });
      } else {
        console.log('   📝 Final state is empty');
      }
    } catch (error) {
      console.log(`⚠️  Could not retrieve final state: ${error.message}`);
    }

    // Show data history if available
    if (receivedUpdates.length > 0) {
      console.log('\n📈 Update History (last 5):');
      const recentUpdates = receivedUpdates.slice(-5);
      recentUpdates.forEach((update, index) => {
        const timeStr = update.timestamp.toLocaleTimeString();
        console.log(`   ${index + 1}. [${timeStr}] ${update.joints.length} joint(s) updated`);
      });
    }

    if (receivedStates.length > 0) {
      console.log('\n📊 State Sync History (last 3):');
      const recentStates = receivedStates.slice(-3);
      recentStates.forEach((stateUpdate, index) => {
        const timeStr = stateUpdate.timestamp.toLocaleTimeString();
        const jointCount = Object.keys(stateUpdate.state).length;
        console.log(`   ${index + 1}. [${timeStr}] ${jointCount} joint(s) synchronized`);
      });
    }

    console.log('\n🎉 Consumer example completed successfully!');

  } catch (error) {
    console.error('\n❌ Error occurred:', error.message);
    if (error.stack) {
      console.error('Stack trace:', error.stack);
    }
  } finally {
    // Always disconnect and cleanup
    console.log('\n🧹 Cleaning up resources...');
    
    if (consumer.isConnected()) {
      console.log('   Disconnecting from room...');
      await consumer.disconnect();
      console.log('   ✅ Disconnected successfully');
    }
    
    console.log('\n👋 Consumer example finished. Goodbye!');
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