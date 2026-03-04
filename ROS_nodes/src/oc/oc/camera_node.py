#!/usr/bin/env python3
import cv2

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        # Parameters (with defaults)
        self.declare_parameter('device', 0)       # camera index or path to /dev/videoX
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30.0)

        self.device = self.get_parameter('device').value
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = float(self.get_parameter('fps').value)

        self.pub = self.create_publisher(Image, '/cam/raw_image', 10)
        self.bridge = CvBridge()

        self.cap = cv2.VideoCapture(self.device)
        if not self.cap.isOpened():
            raise RuntimeError(f'Cannot open camera device: {self.device}')

        # Try to apply settings (not all cameras/drivers respect these)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        period = 1.0 / max(self.fps, 1e-6)
        self.timer = self.create_timer(period, self.on_timer)

        self.get_logger().info(
            f'Publishing /cam/raw_image from device={self.device} '
            f'({self.width}x{self.height} @ {self.fps} fps)'
        )

    def on_timer(self):
        ok, frame = self.cap.read()
        if not ok or frame is None:
            self.get_logger().warn('Failed to read frame from camera')
            return

        # OpenCV gives BGR by default -> publish as "bgr8"
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'

        self.pub.publish(msg)

    def destroy_node(self):
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
        finally:
            super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = CameraNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()