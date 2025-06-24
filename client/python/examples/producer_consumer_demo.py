#!/usr/bin/env python3
"""
Producer-Consumer Demo - LeRobot Arena

This example demonstrates:
- Producer and multiple consumers working together
- Real-time joint updates
- Emergency stop functionality
- State synchronization
- Connection management
"""

import asyncio
import logging
import random

from lerobot_arena_client import RoboticsConsumer, RoboticsProducer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemoConsumer:
    """Demo consumer that logs all received messages."""

    def __init__(self, name: str, room_id: str):
        self.name = name
        self.room_id = room_id
        self.consumer = RoboticsConsumer("http://localhost:8000")
        self.update_count = 0
        self.state_count = 0

    async def setup(self):
        """Setup consumer with callbacks."""

        def on_joint_update(joints):
            self.update_count += 1
            logger.info(
                f"[{self.name}] Joint update #{self.update_count}: {len(joints)} joints"
            )

        def on_state_sync(state):
            self.state_count += 1
            logger.info(
                f"[{self.name}] State sync #{self.state_count}: {len(state)} joints"
            )

        def on_error(error_msg):
            logger.error(f"[{self.name}] ERROR: {error_msg}")

        def on_connected():
            logger.info(f"[{self.name}] Connected!")

        def on_disconnected():
            logger.info(f"[{self.name}] Disconnected!")

        self.consumer.on_joint_update(on_joint_update)
        self.consumer.on_state_sync(on_state_sync)
        self.consumer.on_error(on_error)
        self.consumer.on_connected(on_connected)
        self.consumer.on_disconnected(on_disconnected)

    async def connect(self):
        """Connect to room."""
        success = await self.consumer.connect(self.room_id, f"demo-{self.name}")
        if success:
            logger.info(f"[{self.name}] Successfully connected to room {self.room_id}")
        else:
            logger.error(f"[{self.name}] Failed to connect to room {self.room_id}")
        return success

    async def disconnect(self):
        """Disconnect from room."""
        if self.consumer.is_connected():
            await self.consumer.disconnect()
        logger.info(
            f"[{self.name}] Final stats: {self.update_count} updates, {self.state_count} states"
        )


async def simulate_robot_movement(producer: RoboticsProducer):
    """Simulate realistic robot movement."""
    # Define some realistic joint ranges for a robotic arm
    joints = {
        "base": {"current": 0.0, "target": 0.0, "min": -180, "max": 180},
        "shoulder": {"current": 0.0, "target": 0.0, "min": -90, "max": 90},
        "elbow": {"current": 0.0, "target": 0.0, "min": -135, "max": 135},
        "wrist": {"current": 0.0, "target": 0.0, "min": -180, "max": 180},
    }

    logger.info("[Producer] Starting robot movement simulation...")

    for step in range(20):  # 20 movement steps
        # Occasionally set new random targets
        if step % 5 == 0:
            for joint_name, joint_data in joints.items():
                joint_data["target"] = random.uniform(
                    joint_data["min"], joint_data["max"]
                )
            logger.info(f"[Producer] Step {step + 1}: New targets set")

        # Move each joint towards its target
        joint_updates = []
        for joint_name, joint_data in joints.items():
            current = joint_data["current"]
            target = joint_data["target"]

            # Simple movement: move 10% towards target each step
            diff = target - current
            move = diff * 0.1
            new_value = current + move

            joint_data["current"] = new_value
            joint_updates.append({"name": joint_name, "value": new_value})

        # Send the joint updates
        await producer.send_joint_update(joint_updates)

        # Add some delay for realistic movement
        await asyncio.sleep(0.5)

    logger.info("[Producer] Movement simulation completed")


async def main():
    """Main demo function."""
    logger.info("=== LeRobot Arena Producer-Consumer Demo ===")

    # Create producer
    producer = RoboticsProducer("http://localhost:8000")

    # Setup producer callbacks
    def on_producer_error(error_msg):
        logger.error(f"[Producer] ERROR: {error_msg}")

    def on_producer_connected():
        logger.info("[Producer] Connected!")

    def on_producer_disconnected():
        logger.info("[Producer] Disconnected!")

    producer.on_error(on_producer_error)
    producer.on_connected(on_producer_connected)
    producer.on_disconnected(on_producer_disconnected)

    try:
        # Create room and connect producer
        room_id = await producer.create_room()
        logger.info(f"Created room: {room_id}")

        success = await producer.connect(room_id, "robot-controller")
        if not success:
            logger.error("Failed to connect producer!")
            return

        # Create multiple consumers
        consumers = []
        consumer_names = ["visualizer", "logger", "safety-monitor"]

        for name in consumer_names:
            consumer = DemoConsumer(name, room_id)
            await consumer.setup()
            consumers.append(consumer)

        # Connect all consumers
        logger.info("Connecting consumers...")
        for consumer in consumers:
            await consumer.connect()
            await asyncio.sleep(0.1)  # Small delay between connections

        # Send initial state
        logger.info("[Producer] Sending initial state...")
        initial_state = {"base": 0.0, "shoulder": 0.0, "elbow": 0.0, "wrist": 0.0}
        await producer.send_state_sync(initial_state)
        await asyncio.sleep(1)

        # Start robot movement simulation
        movement_task = asyncio.create_task(simulate_robot_movement(producer))

        # Let it run for a bit
        await asyncio.sleep(5)

        # Demonstrate emergency stop
        logger.info("🚨 [Producer] Sending emergency stop!")
        await producer.send_emergency_stop(
            "Demo emergency stop - testing safety systems"
        )

        # Wait for movement to complete
        await movement_task

        # Final state check
        logger.info("=== Final Demo Summary ===")
        for consumer in consumers:
            logger.info(
                f"[{consumer.name}] Received {consumer.update_count} updates, {consumer.state_count} states"
            )

        logger.info("Demo completed successfully!")

    except Exception as e:
        logger.error(f"Demo error: {e}")
    finally:
        # Cleanup
        logger.info("Cleaning up...")

        # Disconnect all consumers
        for consumer in consumers:
            await consumer.disconnect()

        # Disconnect producer
        if producer.is_connected():
            await producer.disconnect()

        logger.info("Demo cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
