"""
Backend Server - Sistem Distribusi
Menerima request dari Load Balancer, memproses, dan mengirim response.
Usage: python server.py <port>
"""

import socket
import threading
import sys
import time
from datetime import datetime


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def handle_client(conn, addr, server_name, port):
    """Menangani koneksi dari load balancer."""
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data:
            return

        print(f"[{get_timestamp()}] {server_name} | Menerima request: \"{data}\"")

        # Simulasi proses (delay kecil)
        processing_time = 0.1
        time.sleep(processing_time)

        # Buat response
        response = (
            f"Response dari {server_name} (port {port}) | "
            f"Request: \"{data}\" | "
            f"Diproses dalam {processing_time}s"
        )

        conn.sendall(response.encode("utf-8"))
        print(f"[{get_timestamp()}] {server_name} | Response dikirim ke {addr}")

    except ConnectionResetError:
        print(f"[{get_timestamp()}] {server_name} | Koneksi terputus dari {addr}")
    except Exception as e:
        print(f"[{get_timestamp()}] {server_name} | Error: {e}")
    finally:
        conn.close()


def start_server(port):
    """Menjalankan backend server pada port tertentu."""
    server_name = f"Server-{port}"

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind(("127.0.0.1", port))
        server_socket.listen(5)
        print(f"[{get_timestamp()}] {server_name} | Berjalan di 127.0.0.1:{port}")
        print(f"[{get_timestamp()}] {server_name} | Menunggu koneksi...")

        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr, server_name, port),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] {server_name} | Dihentikan.")
    except OSError as e:
        print(f"[{get_timestamp()}] {server_name} | Error: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python server.py <port>")
        print("Contoh: python server.py 9001")
        sys.exit(1)

    port = int(sys.argv[1])
    start_server(port)
