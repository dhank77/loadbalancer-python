"""
Load Balancer - Sistem Distribusi
Menerima request dari clients dan mendistribusikan ke backend servers
menggunakan algoritma Round-Robin.
Usage: python load_balancer.py
"""

import socket
import threading
import sys
import time
from datetime import datetime

# Konfigurasi backend servers
BACKEND_SERVERS = [
    ("127.0.0.1", 9001),
    ("127.0.0.1", 9002),
    ("127.0.0.1", 9003),
]

LOAD_BALANCER_HOST = "127.0.0.1"
LOAD_BALANCER_PORT = 8000

# Round-robin counter (thread-safe)
current_server_index = 0
index_lock = threading.Lock()

# Statistik
stats = {port: 0 for _, port in BACKEND_SERVERS}
stats_lock = threading.Lock()

# Batas maksimal koneksi per server
MAX_CONNECTIONS_PER_SERVER = 5
# Semaphore untuk setiap backend server guna membatasi load
server_semaphores = {port: threading.Semaphore(MAX_CONNECTIONS_PER_SERVER) for _, port in BACKEND_SERVERS}


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def check_server_health(host, port, timeout=1):
    """Cek apakah backend server aktif."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def get_next_server():
    """Pilih server berikutnya dengan Round-Robin (skip yang tidak aktif atau penuh)."""
    global current_server_index

    attempts = 0
    while attempts < len(BACKEND_SERVERS):
        # Lock HANYA digunakan saat mengambil dan mengubah indeks server
        # Ini mencegah blocking thread lain saat fungsi check_server_health berjalan
        with index_lock:
            server = BACKEND_SERVERS[current_server_index]
            current_server_index = (current_server_index + 1) % len(BACKEND_SERVERS)

        server_host, server_port = server

        # Cek apakah server ini masih bisa menerima koneksi (semaphore tidak kehabisan)
        # acquiring dengan non-blocking (blocking=False), return True jika berhasil acquired lock
        if server_semaphores[server_port].acquire(blocking=False):
            # lock semaphore berhasil didapatkan, maka cek health-nya
            if check_server_health(server_host, server_port):
                return server
            else:
                # Jika health check gagal, kembalikan ketersediaan koneksi pada semaphore
                server_semaphores[server_port].release()
                print(f"[{get_timestamp()}] Load Balancer | Server {server_port} tidak aktif, skip...")
        else:
            print(f"[{get_timestamp()}] Load Balancer | Server {server_port} sedang sibuk (MAX koneksi tercapai), skip...")
        
        attempts += 1

    return None


def forward_request(client_conn, client_addr):
    """Teruskan request dari client ke backend server."""
    server = None
    try:
        # Terima request dari client
        data = client_conn.recv(4096).decode("utf-8")
        if not data:
            return

        print(f"\n[{get_timestamp()}] Load Balancer | Request diterima dari {client_addr}")
        print(f"[{get_timestamp()}] Load Balancer | Data: \"{data}\"")

        # Pilih backend server (Round-Robin dengan batasan koneksi)
        server = get_next_server()
        if server is None:
            error_msg = "Error: Semua backend server tidak aktif atau sedang sibuk!"
            print(f"[{get_timestamp()}] Load Balancer | {error_msg}")
            client_conn.sendall(error_msg.encode("utf-8"))
            return

        server_host, server_port = server
        print(f"[{get_timestamp()}] Load Balancer | Meneruskan ke Server-{server_port} (Round-Robin)")

        # Koneksi ke backend server
        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_socket.settimeout(5)

        try:
            backend_socket.connect((server_host, server_port))
            backend_socket.sendall(data.encode("utf-8"))

            # Terima response dari backend
            response = backend_socket.recv(4096).decode("utf-8")
            backend_socket.close()

            # Update statistik
            with stats_lock:
                stats[server_port] += 1

            # Kirim response ke client
            client_conn.sendall(response.encode("utf-8"))
            print(f"[{get_timestamp()}] Load Balancer | Response dari Server-{server_port} diteruskan ke client")

        except (ConnectionRefusedError, socket.timeout) as e:
            error_msg = f"Error: Gagal terhubung ke Server-{server_port}: {e}"
            print(f"[{get_timestamp()}] Load Balancer | {error_msg}")
            client_conn.sendall(error_msg.encode("utf-8"))
            backend_socket.close()

    except ConnectionResetError:
        print(f"[{get_timestamp()}] Load Balancer | Koneksi terputus dari {client_addr}")
    except Exception as e:
        print(f"[{get_timestamp()}] Load Balancer | Error: {e}")
    finally:
        client_conn.close()
        # Jika semaphore server pernah di-acquire saat forward_request, lepaskan kuncinya sekarang
        # Kita perlu mengecek "server" ada karena bisa jadi gagal mendapatkan server dari "get_next_server"
        if server is not None:
            server_semaphores[server[1]].release()


def print_stats():
    """Tampilkan statistik distribusi."""
    print(f"\n{'='*60}")
    print(f"  STATISTIK DISTRIBUSI LOAD BALANCER")
    print(f"{'='*60}")
    total = sum(stats.values())
    for port, count in stats.items():
        percentage = (count / total * 100) if total > 0 else 0
        bar = "█" * int(percentage / 5)
        print(f"  Server-{port}: {count:3d} request ({percentage:5.1f}%) {bar}")
    print(f"  {'─'*40}")
    print(f"  Total    : {total} request")
    print(f"{'='*60}\n")


def start_load_balancer():
    """Menjalankan load balancer."""
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        lb_socket.bind((LOAD_BALANCER_HOST, LOAD_BALANCER_PORT))
        lb_socket.listen(10)

        print(f"{'='*60}")
        print(f"  LOAD BALANCER - Sistem Distribusi")
        print(f"{'='*60}")
        print(f"[{get_timestamp()}] Load Balancer | Berjalan di {LOAD_BALANCER_HOST}:{LOAD_BALANCER_PORT}")
        print(f"[{get_timestamp()}] Load Balancer | Algoritma: Round-Robin")
        print(f"[{get_timestamp()}] Load Balancer | Backend Servers:")
        for host, port in BACKEND_SERVERS:
            status = "✓ Aktif" if check_server_health(host, port) else "✗ Tidak Aktif"
            print(f"  → {host}:{port} [{status}]")
        print(f"[{get_timestamp()}] Load Balancer | Menunggu koneksi dari client...\n")

        while True:
            client_conn, client_addr = lb_socket.accept()
            thread = threading.Thread(
                target=forward_request,
                args=(client_conn, client_addr),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        print_stats()
        print(f"[{get_timestamp()}] Load Balancer | Dihentikan.")
    except OSError as e:
        print(f"[{get_timestamp()}] Load Balancer | Error: {e}")
    finally:
        lb_socket.close()


if __name__ == "__main__":
    start_load_balancer()
