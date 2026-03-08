import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy
import cv2
import numpy as np

class VisionProcessor(Node):
    def __init__(self):
        """
        Инициализация ноды: настройка сети, паблишеров и подписчиков.
        """
        super().__init__('vision_processor_node')
        
        # Настройка QoS: Best Effort позволяет работать быстрее через Ethernet (не ждем потерянные пакеты)
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)

        # Подписка на "сырое" изображение от камеры
        self.sub = self.create_subscription(Image, '/cam/raw_image', self.image_callback, qos)
        
        # Паблишер для передачи обрезанного кадра (Кропа) обратно в ROS
        self.crop_pub = self.create_publisher(Image, '/vision/cropped_image', 10)
        
        # Паблишер для отправки списка координат (пчелы и цветы)
        self.objects_pub = self.create_publisher(Float32MultiArray, '/vision/detected_objects', 10)
        
        # Инструмент для конвертации ROS сообщений в формат OpenCV (numpy)
        self.bridge = CvBridge()

    def get_crop(self, frame):
        """
        ФУНКЦИЯ КРОПА: Вырезает центральную часть изображения.
        """
        h, w = frame.shape[:2]
        # Координаты обрезки (в данном случае центр кадра)
        cropped = frame[h//4:3*h//4, w//4:3*w//4]
        return cropped

    def detect_objects(self, cropped_frame):
        """
        ФУНКЦИЯ ДЕТЕКЦИИ: Здесь должна быть ваша логика поиска (YOLO, OpenCV контуры и т.д.).
        Сейчас здесь имитация (заглушка) данных.
        """
        # Имитируем найденные координаты пчелок и цветов
        bees = [[10.5, 25.3], [44.0, 80.1]] 
        flowers = [[120.0, 10.5], [200.2, 150.0], [5.0, 5.0]]
        return bees, flowers

    def pack_data(self, bees, flowers):
        """
        ФУНКЦИЯ УПАКОВКИ: Превращает списки списков в плоский массив для отправки по сети.
        Формат: [кол-во_пчел, x,y, x,y..., кол-во_цветов, x,y, x,y...]
        """
        data = []
        
        # Упаковываем пчел
        data.append(float(len(bees)))
        for b in bees:
            data.extend([float(b[0]), float(b[1])])
            
        # Упаковываем цветы
        data.append(float(len(flowers)))
        for f in flowers:
            data.extend([float(f[0]), float(f[1])])
            
        return Float32MultiArray(data=data)

    def image_callback(self, msg):
        """
        ОСНОВНОЙ ЦИКЛ: Вызывается автоматически при получении каждого кадра.
        """
        try:
            # 1. Конвертируем сообщение в картинку OpenCV
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # 2. Получаем Кроп
            cropped = self.get_crop(frame)
            
            # 3. Публикуем Кроп (отправляем обратно в систему)
            crop_msg = self.bridge.cv2_to_imgmsg(cropped, encoding="bgr8")
            self.crop_pub.publish(crop_msg)

            # 4. Ищем объекты (пчел и цветы)
            bees, flowers = self.detect_objects(cropped)

            # 5. Упаковываем координаты и ПУБЛИКУЕМ
            msg_to_send = self.pack_data(bees, flowers)
            self.objects_pub.publish(msg_to_send)

            # 6. Визуализация (Окно предпросмотра)
            cv2.imshow("Vision Monitor", cropped)
            cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f'Ошибка в Vision Node: {e}')
            # Заглушка при ошибке: отправляем пустой список (0 пчел, 0 цветов)
            self.objects_pub.publish(Float32MultiArray(data=[0.0, 0.0]))

def main():
    rclpy.init()
    node = VisionProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Нода остановлена пользователем')
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()