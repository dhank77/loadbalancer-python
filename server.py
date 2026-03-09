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


import fcntl
import os

DATABASE_FILE = "database.txt"

def handle_client(conn, addr, server_name, port):
    """Menangani koneksi dari load balancer dan menulis ke database bersaman."""
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data:
            return

        print(f"[{get_timestamp()}] {server_name} | Menerima request: \"{data}\"")

        # 1. Simulasi memproses tugas (CPU-bound / I/O-bound simulation)
        processing_time = 0.5
        time.sleep(processing_time)
        
        # 2. Persiapkan data log yang akan ditulis
        log_entry = f"[{get_timestamp()}] {server_name} memproses '{data}' dari {addr[0]}\n"

        # 3. Distributed Lock & Tulis ke Shared Database
        # Buka file dalam mode append ('a')
        with open(DATABASE_FILE, "a") as db_file:
            print(f"[{get_timestamp()}] {server_name} | Menunggu lock pada {DATABASE_FILE}...")
            # Mengakuisisi lock secara B EKSKLUSIF dan BLOCKING
            # Jika proses (server) lain sedang memegang lock, eksekusi akan terhenti disini (sleep)
            # sampai lock dilepaskan oleh server lain.
            fcntl.flock(db_file.fileno(), fcntl.LOCK_EX)
            try:
                print(f"[{get_timestamp()}] {server_name} | Lock didapatkan, menulis ke database...")
                db_file.write(log_entry)
                # Pastikan data benar-benar tersimpan ke disk
                db_file.flush()
                os.fsync(db_file.fileno())
                print(f"[{get_timestamp()}] {server_name} | Penulisan selesai.")
            finally:
                # Lepaskan lock
                fcntl.flock(db_file.fileno(), fcntl.LOCK_UN)
                print(f"[{get_timestamp()}] {server_name} | Lock dilepaskan.")

        # 4. Buat response untuk dikembalikan ke Client
        response = (
            f"Response dari {server_name} (port {port}) | "
            f"Tugas '{data}' selesai diproses dalam {processing_time}s dan dicatat ke DB."
        )

        conn.sendall(response.encode("utf-8"))
        print(f"[{get_timestamp()}] {server_name} | Response dikirim kembali ke Load Balancer")

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
