## ROS 2 Python Node — Reference Card

## Before writing any node — ask these four questions

    # 1. What does this node SEND?       → publishers
    # 2. What does this node RECEIVE?    → subscribers
    # 3. What does it need to REMEMBER?  → internal state (self.xxx)
    # 4. What DRIVES its behavior?       → timer (periodic) or subscriber (reactive)

## When to use which type

    # sensor / fake data publisher  → Type 1 (publisher only)
    # logger / monitor / checker    → Type 2 (subscriber only)
    # actuator / simulator          → Type 3 (sub + pub + timer)
    # controller / estimator        → Type 4 (multi-sub + pub + timer)

## Type 1 — Publisher only

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

## Type 2 — Subscriber only

    class MySubscriber(Node):
    
    def __init__(self):
        super().__init__('my_subscriber')
        self.sub = self.create_subscription(PoseStamped, '/my/topic', self.on_message, 10)
        self.get_logger().info('started')

    def on_message(self, msg):
        x = msg.pose.position.x
        self.get_logger().info(f'received: x={x:.2f}')
        if x > 10.0:
            self.get_logger().warn(f'x too large: {x:.2f}')

## Type 3 — Subscriber + Publisher (reactive)

    class MyReactiveNode(Node):
    
    def __init__(self):
        super().__init__('my_reactive_node')
        self.sub = self.create_subscription(PoseStamped, '/my/input', self.on_input, 10)
        self.pub = self.create_publisher(PoseStamped, '/my/output', 10)
        self.latest_input = None
        self.dt = 0.1
        self.create_timer(self.dt, self.update)
        self.get_logger().info('started')

    def on_input(self, msg):
        self.latest_input = msg

    def update(self):
        if self.latest_input is None:
            return
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        self.pub.publish(msg)

## Type 4 — Controller

    class MyController(Node):
    def __init__(self):
        super().__init__('my_controller')
        self.sub_current = self.create_subscription(PoseStamped, '/current', self.on_current, 10)
        self.sub_desired = self.create_subscription(PoseStamped, '/desired', self.on_desired, 10)
        self.pub_cmd = self.create_publisher(PoseStamped, '/cmd', 10)
        self.current = None
        self.desired = None
        self.Kp = 0.5
        self.create_timer(0.1, self.control_loop)
        self.get_logger().info('started')

    def on_current(self, msg):
        self.current = msg

    def on_desired(self, msg):
        self.desired = msg

    def control_loop(self):
        if self.current is None or self.desired is None:
            self.get_logger().info('waiting...', throttle_duration_sec=2.0)
            return
        ex = self.desired.pose.position.x - self.current.pose.position.x
        ey = self.desired.pose.position.y - self.current.pose.position.y
        ez = self.desired.pose.position.z - self.current.pose.position.z
        self.get_logger().info(f'error=({ex:.2f},{ey:.2f},{ez:.2f})')
