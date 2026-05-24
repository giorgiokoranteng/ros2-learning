# Session 01 — ROS 2 Foundations

## Concepts learned

## Nodes vs Topics
    - Node = process that does one job
    - Topic = named channel (passive, just a name)
    - Nodes never talk directly — only through topics

## Pub/Sub model
    - Publisher fires on its own timer — never waits to be asked
    - Subscriber receives every message via callback
    - Discovery automatic via DDS

## Event loop
    - rclpy.spin(node) dispatches callbacks
    - Never use while True inside a node
    - Timer drives periodic behavior
    - Subscriber callback drives reactive behavior


