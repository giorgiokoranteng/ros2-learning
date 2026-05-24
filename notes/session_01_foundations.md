# Session 01 — ROS 2 Foundations

## Concepts learned

# Nodes vs Topics
# - Node = process that does one job
# - Topic = named channel (passive, just a name)
# - Nodes never talk directly — only through topics

# Pub/Sub model
# - Publisher fires on its own timer — never waits to be asked
# - Subscriber receives every message via callback
# - Discovery automatic via DDS

# Event loop
# - rclpy.spin(node) dispatches callbacks
# - Never use while True inside a node
# - Timer drives periodic behavior
# - Subscriber callback drives reactive behavior

## Nodes built

# pose_publisher      → Type 1 → publishes fake pose on /nautilus/pose
# pose_monitor        → Type 2 → monitors /nautilus/pose, warns if out of bounds
# attitude_controller → Type 4 → computes error, publishes cmd
# simulated_plant     → Type 3 → reads cmd, moves vehicle, publishes new pose

## The closed control loop

# desired_pose → attitude_controller → /nautilus/cmd → simulated_plant
#                      up                                      down
#                      └──────── /nautilus/pose ───────────────┘

## Key patterns

# Proportional control: cmd = Kp * error
# Sample and hold: subscriber stores, timer computes
# Guard clause: if self.current is None or self.desired is None: return
# symlink-install: edit Python → run immediately, no rebuild

## Maps to Nautilus

# pose_publisher      → IMU + state estimator
# pose_monitor        → safety / fault detection
# attitude_controller → YOUR actual task
# simulated_plant     → Gazebo / real hardware

## Next session

# Write pose_monitor from skeleton
# Write simulated_plant from skeleton
# Stage 4: Parameters — tune Kp at runtime
# Stage 5: Launch files
# Stage 6: tf2 coordinate frames
