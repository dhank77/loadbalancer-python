import subprocess
import time
import os

print("Memulai Simulasi Sistem Fault Tolerance...")

# Hapus database lama jika ada
if os.path.exists("database.txt"):
    os.remove("database.txt")

# 1. Jalankan hanya 2 Backend Server
servers = []
# KITA SENGAJA MEMATIKAN SERVER 9003 UNTUK UJI COBA FAULT TOLERANCE
for port in [9001, 9002]: 
    p = subprocess.Popen(["python3", "server.py", str(port)])
    servers.append(p)
    print(f"[+] Started Server pada port {port}")

print("[-] PERINGATAN: Server-9003 sengaja dimatikan untuk demonstrasi Fault Tolerance!")

time.sleep(1) # Tunggu server siap

# 2. Jalankan Load Balancer
lb = subprocess.Popen(["python3", "load_balancer.py"])
print("[+] Started Load Balancer pada port 8000")

time.sleep(1) # Tunggu LB siap

# 3. Jalankan Client bersamaan
clients = []
print("Memulai 3 Client secara bersamaan (Untuk memastikan Load Balancer akan menunjuk ke 9003)...")
for client_id in range(1, 4):
    p = subprocess.Popen(["python3", "client.py", str(client_id)])
    clients.append(p)

# Tunggu semua client selesai
for c in clients:
    c.wait()

print("\n--- Semua Client Selesai ---")

# Tunggu sejenak agar server selesai menulis sisa antrian (jika ada)
time.sleep(2)

# Hentikan LB & Server
print("Menghentikan Load Balancer dan Servers...")
lb.terminate()
for s in servers:
    s.terminate()

print("\n=== ISI DATABASE BERSAMA (database.txt) ===")
if os.path.exists("database.txt"):
    with open("database.txt", "r") as f:
        print(f.read())
else:
    print("Database tidak ditemukan!")

print("Simulasi Selesai.")
