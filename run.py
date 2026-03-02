"""
Runner Script - Sistem Distribusi
Menjalankan semua komponen: 3 servers, 1 load balancer, dan 3 clients.
Usage: python run.py
"""

import subprocess
import sys
import time
import signal
import os
from datetime import datetime

# Konfigurasi
SERVER_PORTS = [9001, 9002, 9003]
NUM_CLIENTS = 3
STARTUP_DELAY = 1  # Delay antar komponen (detik)

processes = []


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def cleanup(signum=None, frame=None):
    """Hentikan semua proses."""
    print(f"\n\n{'='*60}")
    print(f"  MENGHENTIKAN SEMUA KOMPONEN...")
    print(f"{'='*60}")
    for name, proc in processes:
        if proc.poll() is None:
            proc.terminate()
            print(f"  ✗ {name} dihentikan")
    print(f"{'='*60}\n")
    sys.exit(0)


def main():
    # Tangkap Ctrl+C
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    print(f"\n{'='*60}")
    print(f"  SISTEM DISTRIBUSI DENGAN LOAD BALANCER")
    print(f"  Algoritma: Round-Robin")
    print(f"{'='*60}")
    print(f"[{get_timestamp()}] Memulai semua komponen...\n")

    # 1. Jalankan 3 Backend Servers
    print(f"[{get_timestamp()}] ── Menjalankan Backend Servers ──")
    for port in SERVER_PORTS:
        proc = subprocess.Popen(
            [python_exe, os.path.join(script_dir, "server.py"), str(port)],
            cwd=script_dir
        )
        processes.append((f"Server-{port}", proc))
        print(f"[{get_timestamp()}] ✓ Server-{port} dimulai (PID: {proc.pid})")

    time.sleep(STARTUP_DELAY)

    # 2. Jalankan Load Balancer
    print(f"\n[{get_timestamp()}] ── Menjalankan Load Balancer ──")
    proc = subprocess.Popen(
        [python_exe, os.path.join(script_dir, "load_balancer.py")],
        cwd=script_dir
    )
    processes.append(("Load Balancer", proc))
    print(f"[{get_timestamp()}] ✓ Load Balancer dimulai (PID: {proc.pid})")

    time.sleep(STARTUP_DELAY)

    # 3. Jalankan 3 Clients
    print(f"\n[{get_timestamp()}] ── Menjalankan Clients ──")
    client_procs = []
    for i in range(1, NUM_CLIENTS + 1):
        proc = subprocess.Popen(
            [python_exe, os.path.join(script_dir, "client.py"), str(i)],
            cwd=script_dir
        )
        processes.append((f"Client-{i}", proc))
        client_procs.append(proc)
        print(f"[{get_timestamp()}] ✓ Client-{i} dimulai (PID: {proc.pid})")
        time.sleep(0.3)  # Sedikit delay antar client

    # Tunggu semua client selesai
    print(f"\n[{get_timestamp()}] Menunggu semua client selesai...\n")
    for proc in client_procs:
        proc.wait()

    time.sleep(1)

    print(f"\n{'='*60}")
    print(f"  SEMUA CLIENT SELESAI")
    print(f"  Tekan Ctrl+C untuk menghentikan servers & load balancer")
    print(f"{'='*60}\n")

    # Tunggu Ctrl+C untuk menghentikan server
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
