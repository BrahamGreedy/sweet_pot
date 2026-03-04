#!/usr/bin/env python3
import socket
import threading
import time
from queue import Queue, Empty

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class EthNode(Node):
    def __init__(self):
        super().__init__('eth_node')

        # Параметры сокета
        self.declare_parameter('host', '192.168.0.50')
        self.declare_parameter('port', 9000)
        self.declare_parameter('connect_timeout_s', 2.0)
        self.declare_parameter('reconnect_period_s', 1.0)
        self.declare_parameter('recv_timeout_s', 0.2)
        self.declare_parameter('send_newline', True)  # удобно, если на ESP читаешь по строкам

        self.host = self.get_parameter('host').get_parameter_value().string_value
        self.port = int(self.get_parameter('port').get_parameter_value().integer_value)
        self.connect_timeout_s = float(self.get_parameter('connect_timeout_s').value)
        self.reconnect_period_s = float(self.get_parameter('reconnect_period_s').value)
        self.recv_timeout_s = float(self.get_parameter('recv_timeout_s').value)
        self.send_newline = bool(self.get_parameter('send_newline').value)

        # ROS интерфейсы
        self.pub = self.create_publisher(String, '/esp/data', 10)
        self.sub = self.create_subscription(String, '/server/command', self.on_command, 10)

        # Очередь исходящих команд
        self.tx_q: Queue[str] = Queue()

        # Состояние сокета
        self._sock = None
        self._stop = threading.Event()

        # Поток работы с сокетом (и отправка, и прием)
        self._thr = threading.Thread(target=self._io_loop, daemon=True)
        self._thr.start()

        self.get_logger().info(
            f"eth_node started. Sub: /server/command -> TCP {self.host}:{self.port} -> Pub: /esp/data"
        )

    def on_command(self, msg: String):
        # msg.data ожидаем как JSON-строку (или любую строку)
        payload = msg.data
        if self.send_newline and not payload.endswith('\n'):
            payload += '\n'
        self.tx_q.put(payload)

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.connect_timeout_s)
        s.connect((self.host, self.port))
        s.settimeout(self.recv_timeout_s)  # для recv в цикле
        return s

    def _close_sock(self):
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None

    def _publish_rx(self, text: str):
        out = String()
        out.data = text
        self.pub.publish(out)

    def _io_loop(self):
        rx_buf = b""

        while not self._stop.is_set():
            # 1) Убедимся, что есть соединение
            if self._sock is None:
                try:
                    self._sock = self._connect()
                    self.get_logger().info(f"TCP connected to {self.host}:{self.port}")
                    rx_buf = b""
                except Exception as e:
                    self.get_logger().warn(f"TCP connect failed: {e}")
                    self._close_sock()
                    time.sleep(self.reconnect_period_s)
                    continue

            # 2) Отправка (если есть что отправлять)
            try:
                payload = self.tx_q.get_nowait()
                self._sock.sendall(payload.encode('utf-8', errors='replace'))
            except Empty:
                pass
            except Exception as e:
                self.get_logger().warn(f"TCP send failed: {e}")
                self._close_sock()
                continue

            # 3) Приём
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    # соединение закрыто удаленной стороной
                    self.get_logger().warn("TCP connection closed by peer")
                    self._close_sock()
                    continue

                rx_buf += chunk

                # Если протокол построчный (newline), режем по '\n'
                while b'\n' in rx_buf:
                    line, rx_buf = rx_buf.split(b'\n', 1)
                    text = line.decode('utf-8', errors='replace').strip()
                    if text:
                        self._publish_rx(text)

            except socket.timeout:
                # нормально, просто нет данных сейчас
                pass
            except Exception as e:
                self.get_logger().warn(f"TCP recv failed: {e}")
                self._close_sock()
                continue

    def destroy_node(self):
        self._stop.set()
        self._close_sock()
        super().destroy_node()


def main():
    rclpy.init()
    node = EthNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()