import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import socket
import json # Удобно для парсинга структурированных данных

class SocketNode(Node):
    def __init__(self):
        super().__init__('socket_bridge_node')
        
        self.host = '127.0.0.1'
        self.port = 65432
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(0.5) # Чтобы узел не зависал при ожидании данных
        
        try:
            self.sock.connect((self.host, self.port))
            self.get_logger().info(f'Подключено к {self.host}:{self.port}')
        except Exception as e:
            self.get_logger().error(f'Ошибка подключения: {e}')

        self.timer = self.create_timer(1.0, self.send_socket_data)

    def parse_data(self, raw_data):
        """Функция парсинга входящего протокола"""
        try:
            # Декодируем и убираем лишние пробелы/символы переноса
            decoded_data = raw_data.decode('utf-8').strip()
            
            # Пример парсинга JSON (самый частый вариант)
            # Допустим, сервер шлет: {"status": "ok", "value": 10}
            data = json.loads(decoded_data)
            return data
        except json.JSONDecodeError:
            self.get_logger().error("Ошибка парсинга: неверный формат JSON")
            return None
        except Exception as e:
            self.get_logger().error(f"Ошибка декодирования: {e}")
            return None

    def send_socket_data(self):
        try:
            # 1. Отправка данных
            message = json.dumps({"cmd": "get_telemetry", "id": 1})
            self.sock.sendall((message + '\n').encode('utf-8'))
            
            # 2. Получение и парсинг ответа (чтение до 1024 байт)
            response = self.sock.recv(1024)
            if response:
                parsed_msg = self.parse_data(response)
                if parsed_msg:
                    self.get_logger().info(f'Распарсено: {parsed_msg}')
                    # Здесь можно опубликовать данные в топик ROS
            
        except socket.timeout:
            self.get_logger().warn('Тайм-аут ожидания ответа от сервера')
        except Exception as e:
            self.get_logger().error(f'Ошибка связи: {e}')

def main():
    rclpy.init()
    node = SocketNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.sock.close()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
