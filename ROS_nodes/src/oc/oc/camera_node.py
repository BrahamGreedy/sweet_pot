import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge # Добавили мост для конвертации

class Peredacha(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.pub = self.create_publisher(Image, '/cam/raw_image', 10)
        self.cap = cv2.VideoCapture(0)
        self.bridge = CvBridge() # Инициализируем мост

        # 1. Указываем период (например, 0.1 сек = 10 FPS)
        period = 0.1 
        self.timer = self.create_timer(period, self.on_timer)

    def on_timer(self):
        # 2. Считываем кадр с камеры
        ret, frame = self.cap.read()
        if ret:
            # 3. Конвертируем OpenCV изображение в сообщение ROS 2 и публикуем
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.pub.publish(msg)
            self.get_logger().info('Кадр отправлен')

def main():
    rclpy.init()
    try:
        node = Peredacha()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()



