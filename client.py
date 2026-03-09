"""
Client - Sistem Distribusi
Mengirim request ke Load Balancer dan menampilkan response.
Usage: python client.py <client_id>
"""

import socket
import sys
import time
from datetime import datetime


LOAD_BALANCER_HOST = "127.0.0.1"
LOAD_BALANCER_PORT = 8000

NUM_REQUESTS = 5  # Jumlah request per client


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


import json
import random

def send_request(client_id, request_num):
    """Kirim satu request ke load balancer."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((LOAD_BALANCER_HOST, LOAD_BALANCER_PORT))

        # 1. Buat Payload Tugas dalam bentuk JSON
        task_types = ["Data Processing", "Image Rendering", "Database Query", "Send Email"]
        task_payload = {
            "client_id": client_id,
            "task_id": f"TASK-{client_id}-{request_num}",
            "task_type": random.choice(task_types),
            "timestamp": get_timestamp()
        }
        
        # Konversi ke string JSON (UTF-8)
        message = json.dumps(task_payload)
        sock.sendall(message.encode("utf-8"))
        print(f"[{get_timestamp()}] Client-{client_id} | Mengirim misi: {message}")

        # Terima response
        response = sock.recv(4096).decode("utf-8")
        print(f"[{get_timestamp()}] Client-{client_id} | Menerima Response: \"{response}\"")

        sock.close()
        return True

    except ConnectionRefusedError:
        print(f"[{get_timestamp()}] Client-{client_id} | Error: Load Balancer tidak aktif!")
        return False
    except socket.timeout:
        print(f"[{get_timestamp()}] Client-{client_id} | Error: Timeout!")
        return False
    except Exception as e:
        print(f"[{get_timestamp()}] Client-{client_id} | Error: {e}")
        return False


def start_client(client_id):
    """Menjalankan client dan mengirim beberapa request."""
    print(f"\n{'─'*50}")
    print(f"  CLIENT-{client_id} - Sistem Distribusi")
    print(f"{'─'*50}")
    print(f"[{get_timestamp()}] Client-{client_id} | Mulai mengirim {NUM_REQUESTS} request")
    print(f"[{get_timestamp()}] Client-{client_id} | Target: {LOAD_BALANCER_HOST}:{LOAD_BALANCER_PORT}\n")

    success = 0
    failed = 0

    for i in range(1, NUM_REQUESTS + 1):
        if send_request(client_id, i):
            success += 1
        else:
            failed += 1

        # Delay antara request
        if i < NUM_REQUESTS:
            time.sleep(0.5)

    # Ringkasan
    print(f"\n[{get_timestamp()}] Client-{client_id} | Selesai!")
    print(f"[{get_timestamp()}] Client-{client_id} | Berhasil: {success}/{NUM_REQUESTS}, Gagal: {failed}/{NUM_REQUESTS}")
    print(f"{'─'*50}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python client.py <client_id>")
        print("Contoh: python client.py 1")
        sys.exit(1)

    client_id = sys.argv[1]
    start_client(client_id)
