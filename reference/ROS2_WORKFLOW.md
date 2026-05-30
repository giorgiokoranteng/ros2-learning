# ROS 2 Project Workflow — How to Approach Any ROS Project

> The process and mental method for building ROS systems from scratch.
> Built during the Nautilus UUV project.

---

## Part 1 — Before writing any code

### Step 1: Draw the system architecture

ALWAYS start with a diagram. Never write code before you can draw the data flow.

Ask:
```
- What are the NODES (the processes)?
- What are the TOPICS (the channels between them)?
- Who PUBLISHES what?
- Who SUBSCRIBES to what?
- What MESSAGE TYPE does each topic carry?
```

Draw boxes (nodes) and arrows (topics). Label every arrow with its message type.

Example:
```
sensor_node ──PoseStamped──> /robot/pose ──> controller_node ──Vector3──> /robot/cmd ──> driver_node
```

### Step 2: Identify each node's type

For each node, ask the four questions:
```
1. What does it SEND?       → publishers
2. What does it RECEIVE?    → subscribers
3. What does it REMEMBER?   → internal state
4. What DRIVES it?          → timer or subscriber callback
```

Classify each as:
```
Type 1 — Publisher only       (sensor, fake data, planner)
Type 2 — Subscriber only      (logger, monitor, safety)
Type 3 — Sub + Pub + Timer    (actuator, simulator, transformer)
Type 4 — Controller           (multi-sub + pub + timer)
```

### Step 3: Discover existing topic types

If joining an existing codebase, find out what types are already used:
```bash
ros2 topic list -t                    # all topics + their types
ros2 topic info /some/topic -v        # detail on one topic
ros2 interface show <message_type>    # structure of a message
ros2 node info /some/node             # what a node publishes/subscribes
```

Match your new node to the existing types. Don't invent new types if standard ones fit.

---

## Part 2 — Writing a node

### The three-layer structure

```
LAYER 1 — __init__ (declaration, runs ONCE)
    super().__init__('name')
    publishers
    subscribers
    internal state (self.xxx)
    timer
    log started

LAYER 2 — on_xxx callbacks (reception, store only)
    def on_data(self, msg):
        self.latest = msg

LAYER 3 — timer callback (computation, the actual work)
    def update(self):
        read self.latest
        compute
        publish
```

### Critical rules

```
✅ super().__init__() always first
✅ every callback must be registered (timer or subscription) or it never runs
✅ guard control loops against None
✅ subscriber callbacks just store — never compute
✅ initialize state to None or zero in __init__
✅ always fill header.stamp and header.frame_id

❌ never put work in a subscriber callback
❌ never use while True inside a node
❌ never set config (like Kp) inside the timer loop
❌ never forget the timer (callback defined ≠ callback runs)
```

### The #1 bug to watch for

```
A callback method does NOTHING unless a trigger is registered.

Defined control_loop but forgot create_timer?
→ control_loop never runs. Dead code.

ALWAYS check: is every callback wired to a trigger?
```

---

## Part 3 — Building and running

### After writing a node

```bash
# 1. add entry point to setup.py:
#    'node_name = package.node_file:main',

# 2. build
cd /root/ros2_ws
colcon build --packages-select <pkg> --symlink-install

# 3. source
source install/setup.bash

# 4. run
ros2 run <package> <node>
```

### When to rebuild vs not

```
edited existing .py file        → NO rebuild (symlink-install handles it)
added new node to setup.py      → rebuild required
changed package.xml             → rebuild required
new .msg file                   → rebuild required
```

### Running a multi-node system

```
each node needs its own terminal:
    docker exec -it ros2 bash    (new terminal into container)
    ros2 run <pkg> <node>

start order for controllers:
    1. start the data sources (sensors/plant) first
    2. start the controller
    3. inject commands (ros2 topic pub) last
```

---

## Part 4 — Debugging

### The CLI tools (use these before GUI)

```bash
ros2 node list                    # is my node running?
ros2 topic list -t                # do the topics exist with right types?
ros2 topic echo /topic            # is data actually flowing?
ros2 topic hz /topic              # at what rate?
ros2 topic info /topic -v         # are pub and sub connected? (counts)
ros2 node info /node              # what does my node connect to?
```

### Debugging checklist when nothing happens

```
1. is the node running?           → ros2 node list
2. does the topic exist?          → ros2 topic list
3. is data flowing?               → ros2 topic echo /topic
4. are pub and sub connected?     → ros2 topic info /topic -v
                                     (publisher count, subscription count)
5. right message type both sides? → ros2 topic list -t
6. is the callback registered?    → check create_timer / create_subscription
7. is the guard always returning? → check if data is actually arriving
```

### Common errors and causes

```
ModuleNotFoundError: rclpy        → PyCharm only, ignore (runs in container)
Package not found                 → typo in package name, or forgot to source
No module named 'pkg.node'        → file in wrong folder, or setup.py wrong
entry point error / NoneType      → setup.py format wrong (missing comma!)
node runs but does nothing        → forgot create_timer for the loop
"waiting for data" forever        → data source not running, or topic mismatch
```

---

## Part 5 — The control system pattern

### Closed-loop control architecture

```
desired state ──> CONTROLLER ──> command ──> PLANT/DRIVER ──> actuator
                     ↑                                            │
                     │                                       physical motion
                     │                                            │
                  current state <── SENSOR <────────────────────┘
```

### The roles

```
CONTROLLER  =  computes command from error (your control logic)
              error = desired - current
              cmd = control_law(error)    [P, PI, or PID]

DRIVER      =  translates command to hardware signal (CAN, PWM, serial)
              software node

PLANT       =  the physical system (motors, vehicle, physics)
              hardware

SENSOR      =  measures actual state (IMU, encoders)
              publishes back to controller
```

### Control laws

```
P (proportional):
    cmd = Kp * error
    simple, has steady-state error

PI (proportional-integral):
    cmd = Kp * error + Ki * integral(error)
    eliminates steady-state error
    needs: self.integral (init to 0.0)

PID (proportional-integral-derivative):
    cmd = Kp * error + Ki * integral + Kd * derivative
    eliminates steady-state error + reduces overshoot
    needs: self.integral, self.prev_error (init to 0.0)
```

### Tuning gains

```
1. toy simulation:  useless for tuning (physics too simple)
                    only confirms code works
2. Gazebo:          real tuning (realistic physics, 80% of the way)
3. real hardware:   final fine-tuning (the messy 20%)

manual tuning:      start low, raise until oscillation, back off
                    (Kp small = slow/stable, Kp large = fast/oscillates)

make gains runtime parameters → tune live without rebuilding
```

### Safety additions for real hardware

```python
# clamp commands to physical limits
cmd = max(min_limit, min(max_limit, cmd))

# guard against missing data
if self.current is None or self.desired is None:
    return

# emergency stop override
if self.emergency:
    self.publish_zero()
    return
```

---

## Part 6 — Coordinate frames (when you need tf2)

```
every position is RELATIVE to a frame:
    'world'      → fixed to earth (absolute)
    'odom'       → fixed to start position
    'base_link'  → fixed to vehicle body (moves with it)

frame_id in the header says which frame the numbers are in

tf2 converts between frames:
    desired pose in 'odom' frame
    but actuator commands in 'base_link' frame
    → tf2 transforms one to the other

without correct frames → commands go in wrong direction
```

---

## Quick-start checklist for a new ROS project

```
[ ] draw the architecture (nodes + topics + types)
[ ] classify each node (Type 1-4)
[ ] discover existing topic types (ros2 topic list -t)
[ ] write each node (3-layer structure)
[ ] register every callback (timer / subscription)
[ ] add entry points to setup.py
[ ] colcon build --symlink-install
[ ] source install/setup.bash
[ ] run nodes (data sources first, controller, then commands)
[ ] debug with CLI tools (echo, hz, info)
[ ] visualize in Foxglove if helpful
[ ] tune gains (Gazebo → hardware)
```

---

*Built during ROS 2 Humble learning — Nautilus UUV project*
