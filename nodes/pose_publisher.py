"""
pose_publisher.py — Type 1 (Publisher only)
Written from scratch during Session 01.
Publishes fake vehicle pose on /nautilus/pose.
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class PosePublisher(Node):

    def __init__(self):
        super().__init__('pose_publisher')
        self.publisher = self.create_publisher(PoseStamped, '/nautilus/pose', 10)
        self.t = 0.0
        self.create_timer(1.0, self.tick)
        self.get_logger().info('Pose Publisher started')

    def tick(self):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'

        msg.pose.position.x = math.cos(self.t * 0.1)
        msg.pose.position.y = math.sin(self.t * 0.1)
        msg.pose.position.z = -2.0 + 0.5 * math.sin(self.t * 0.3)

        msg.pose.orientation.x = 0.0
        msg.pose.orientation.y = 0.0
        msg.pose.orientation.z = 0.0
        msg.pose.orientation.w = 1.0

        self.publisher.publish(msg)
        self.get_logger().info(
            f'x={msg.pose.position.x:.2f} '
            f'y={msg.pose.position.y:.2f} '
            f'z={msg.pose.position.z:.2f}'
        )
        self.t += 1.0


def main():
    rclpy.init()
    node = PosePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
