# ROS 2 CLI Commands

## Container
docker start ros2
docker exec -it ros2 bash

## Build
cd /root/ros2_ws
colcon build --packages-select <pkg> --symlink-install
source install/setup.bash
ros2 run <package> <node>

## Nodes
ros2 node list
ros2 node info /node_name

## Topics
ros2 topic list
ros2 topic list -t
ros2 topic echo /topic
ros2 topic echo /topic --once
ros2 topic hz /topic
ros2 topic info /topic -v

## Services
ros2 service list
ros2 service call /service <type> <args>

## Parameters
ros2 param list
ros2 param get /node_name param
ros2 param set /node_name param value

## Messages
ros2 interface show geometry_msgs/msg/PoseStamped

## Foxglove
ros2 run foxglove_bridge foxglove_bridge
