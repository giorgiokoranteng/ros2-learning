# ROS 2 Python Node — Complete Reference

> Mental model + skeletons + rules for building any ROS 2 node from scratch.
> Built during the Nautilus UUV project.

---

## Table of contents

1. [The mental model](#1-the-mental-model)
2. [The four node types](#2-the-four-node-types)
3. [Complete skeletons](#3-complete-skeletons)
4. [Reference rules](#4-reference-rules)
5. [Common patterns](#5-common-patterns)

---

## 1. The mental model

### Every node is three layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — DECLARATION (__init__)                                   │
│  "Here is what I am and what I connect to"                          │
│                                                                      │
│    super().__init__('name')           → register with ROS           │
│    create_publisher(...)              → I will SEND on this topic   │
│    create_subscription(..., on_x)     → I will RECEIVE, call on_x   │
│    self.variable = initial_value      → I need to remember this     │
│    create_timer(period, update)       → call update() periodically  │
│    get_logger().info('started')       → confirm I'm alive           │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — RECEPTION (on_something methods)                         │
│  "Here is what I do when data arrives"                              │
│                                                                      │
│    def on_cmd(self, msg):                                           │
│        self.latest_cmd = msg          → just store, nothing else    │
│                                       → keep it fast, ROS is waiting│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — COMPUTATION (update/tick/control_loop)                   │
│  "Here is where the actual work happens"                            │
│                                                                      │
│    def update(self):                                                │
│        read self.latest_cmd           → what arrived                │
│        compute something              → the actual logic            │
│        publish result                 → send output                 │
└─────────────────────────────────────────────────────────────────────┘
```

### The runtime flow

```
1. __init__ runs ONCE      →  declares everything, wires up connections
2. spin() starts           →  ROS takes control, watches for events
3. message arrives         →  ROS calls on_something(msg) → stores data
4. timer fires             →  ROS calls update() → reads → computes → publishes
5. repeat 3 and 4 forever  →  until Ctrl-C
```

### The two callback types

| Triggered by | Method | Argument | Rule |
|---|---|---|---|
| Incoming message | `on_something(self, msg)` | `msg` arrives populated | Just store, never compute |
| Timer | `update(self)` / `tick(self)` | none (reads `self.xxx`) | Compute, publish, update state |

**Why separate them**: decouples message rate from control rate. Sensor data may jitter, but your control loop runs at a stable rate regardless.

---

## 2. The four node types

| Type | Pattern | Example | Use for |
|---|---|---|---|
| **1** | Publisher only | `pose_publisher` | sensor driver, fake data, mission planner |
| **2** | Subscriber only | `pose_monitor` | logger, safety monitor, data recorder |
| **3** | Sub + Pub + Timer | `simulated_plant` | actuator driver, simulator, transformer |
| **4** | Multi-sub + Pub + Timer | `attitude_controller` | controller, estimator, fusion |

### One-line summaries

```
Type 1:  timer → tick() → publish
Type 2:  message → on_x() → react
Type 3:  message → on_x() → store ──┐
         timer → update() ──────────┴→ compute → publish
Type 4:  message1 → on_current() → store ──┐
         message2 → on_desired() → store ──┤
         timer → control_loop() ───────────┴→ error → cmd → publish
```

---

## 3. Complete skeletons

### Type 1 — Publisher only

```python
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class MyPublisher(Node):
    def __init__(self):
        super().__init__('my_publisher')
        self.pub = self.create_publisher(PoseStamped, '/my/topic', 10)
        self.state = 0.0
        self.create_timer(1.0, self.tick)
        self.get_logger().info('started')

    def tick(self):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.pose.position.x = self.state
        msg.pose.orientation.w = 1.0
        self.pub.publish(msg)
        self.state += 1.0


def main():
    rclpy.init()
    node = MyPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

### Type 2 — Subscriber only

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class MySubscriber(Node):
    def __init__(self):
        super().__init__('my_subscriber')
        self.sub = self.create_subscription(
            PoseStamped, '/my/topic', self.on_message, 10
        )
        self.count = 0
        self.get_logger().info('started')

    def on_message(self, msg):
        self.count += 1
        x = msg.pose.position.x
        self.get_logger().info(f'[#{self.count}] x={x:.2f}')
        if x > 10.0:
            self.get_logger().warn(f'x too large: {x:.2f}')


def main():
    rclpy.init()
    node = MySubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

### Type 3 — Subscriber + Publisher + Timer

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Vector3


class MyReactiveNode(Node):
    def __init__(self):
        super().__init__('my_reactive_node')

        # subscriber — input
        self.sub = self.create_subscription(
            Vector3, '/my/input', self.on_input, 10
        )

        # publisher — output
        self.pub = self.create_publisher(PoseStamped, '/my/output', 10)

        # internal state
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.latest_input = Vector3()

        # timer drives output at fixed rate
        self.dt = 0.1
        self.create_timer(self.dt, self.update)

        self.get_logger().info('started')

    def on_input(self, msg):
        self.latest_input = msg

    def update(self):
        # integrate input into state
        self.x += self.latest_input.x * self.dt
        self.y += self.latest_input.y * self.dt
        self.z += self.latest_input.z * self.dt

        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.pose.position.x = self.x
        msg.pose.position.y = self.y
        msg.pose.position.z = self.z
        msg.pose.orientation.w = 1.0
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = MyReactiveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

### Type 4 — Controller

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Vector3


class MyController(Node):
    def __init__(self):
        super().__init__('my_controller')

        # subscribers — two inputs
        self.sub_current = self.create_subscription(
            PoseStamped, '/current', self.on_current, 10
        )
        self.sub_desired = self.create_subscription(
            PoseStamped, '/desired', self.on_desired, 10
        )

        # publisher — command output
        self.pub_cmd = self.create_publisher(Vector3, '/cmd', 10)

        # internal state — None until first message arrives
        self.current = None
        self.desired = None

        # control gain (move to ROS parameter for runtime tuning)
        self.Kp = 0.5

        # control loop at fixed rate
        self.create_timer(0.1, self.control_loop)

        self.get_logger().info('started')

    def on_current(self, msg):
        self.current = msg

    def on_desired(self, msg):
        self.desired = msg

    def control_loop(self):
        # guard — wait until both signals have arrived
        if self.current is None or self.desired is None:
            self.get_logger().info(
                'waiting for data...',
                throttle_duration_sec=2.0
            )
            return

        # compute error: desired - current
        ex = self.desired.pose.position.x - self.current.pose.position.x
        ey = self.desired.pose.position.y - self.current.pose.position.y
        ez = self.desired.pose.position.z - self.current.pose.position.z

        # proportional control law
        cmd = Vector3()
        cmd.x = self.Kp * ex
        cmd.y = self.Kp * ey
        cmd.z = self.Kp * ez

        self.pub_cmd.publish(cmd)
        self.get_logger().info(
            f'error=({ex:.2f},{ey:.2f},{ez:.2f}) '
            f'cmd=({cmd.x:.2f},{cmd.y:.2f},{cmd.z:.2f})'
        )


def main():
    rclpy.init()
    node = MyController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

## 4. Reference rules

### Method signatures

```python
# create_publisher — 3 arguments
self.pub = self.create_publisher(
    MessageType,       # what you send
    '/topic/name',     # where you send it
    10                 # queue size
)

# create_subscription — 4 arguments
self.sub = self.create_subscription(
    MessageType,       # what you receive
    '/topic/name',     # where you listen
    self.on_x,         # callback when data arrives
    10                 # queue size
)

# create_timer — 2 arguments
self.create_timer(
    period_seconds,    # how often to fire
    self.callback      # what to call
)
```

### __init__ checklist — always in this order

```
1. super().__init__('name')        → always first
2. create_publisher(...)           → outputs
3. create_subscription(...)        → inputs
4. self.state = initial_value      → memory between callbacks
5. create_timer(period, callback)  → heartbeat
6. get_logger().info('started')    → confirmation
```

### Callback rules

```
✅ subscriber callback      → receives msg → just stores it
✅ timer callback           → no arg → reads stored state → computes → publishes
✅ guard control loops      → check None before reading state

❌ never `while True` inside a callback (blocks spin)
❌ never compute heavy logic in a subscriber callback
❌ never call your own callbacks manually — ROS does that
```

### Message rules

```
✅ always fill header.stamp     → self.get_clock().now().to_msg()
✅ always fill header.frame_id  → 'odom', 'base_link', etc.
✅ identity quaternion          → x=0.0, y=0.0, z=0.0, w=1.0
```

### Build rules

```
new node added to setup.py    → colcon build required
existing .py file edited      → NO rebuild needed (symlink-install)
new dependency in package.xml → colcon build required
new .msg file                 → colcon build required
```

### Naming conventions

| Pattern | Use for |
|---|---|
| `on_pose()` | receives pose data |
| `on_cmd()` | receives command data |
| `on_desired()` | receives desired pose |
| `update()` | timer-driven computation (Type 3) |
| `tick()` | timer-driven publish (Type 1) |
| `control_loop()` | timer-driven control (Type 4) |

---

## 5. Common patterns

### Sample and hold

Decouples message arrival rate from computation rate.

```python
# subscriber stores
def on_imu(self, msg):
    self.latest_imu = msg

# timer reads stored value at fixed rate
def control_loop(self):
    use(self.latest_imu)
```

### Guard clause

Protects against startup race conditions.

```python
def control_loop(self):
    if self.current is None or self.desired is None:
        return    # wait until data arrives
    # ...rest of logic
```

### Throttled logging

Log without spamming when waiting.

```python
self.get_logger().info(
    'waiting for data...',
    throttle_duration_sec=2.0    # log every 2s, not 10×/s
)
```

### Reading from a PoseStamped

```python
x = msg.pose.position.x
y = msg.pose.position.y
z = msg.pose.position.z

qx = msg.pose.orientation.x
qy = msg.pose.orientation.y
qz = msg.pose.orientation.z
qw = msg.pose.orientation.w

timestamp = msg.header.stamp
frame = msg.header.frame_id
```

### Building a PoseStamped to publish

```python
msg = PoseStamped()
msg.header.stamp = self.get_clock().now().to_msg()
msg.header.frame_id = 'odom'
msg.pose.position.x = 1.0
msg.pose.position.y = 0.0
msg.pose.position.z = -3.0
msg.pose.orientation.w = 1.0    # identity = no rotation
```

---

## Architecture template

```
INPUT SOURCE              TOPIC                    YOUR NODE
(sensor/operator)           │                         │
        │                   ▼                         │
        └──────────→ /your/input/topic ──────→ on_something() → stores
                                                                    │
                                                                    ▼
                                                              self.stored_data
                                                                    │
                                                              timer fires
                                                                    │
                                                                    ▼
                                                          update()/control_loop()
                                                                    │
                                                                    ▼
YOUR NODE ──────────→ /your/output/topic ──────→ next node reads it
```

---

*Built during ROS 2 Humble learning — Nautilus UUV project*
