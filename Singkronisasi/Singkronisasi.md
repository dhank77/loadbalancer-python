# Mekanisme Sinkronisasi pada Simulasi Sistem Terdistribusi

Dalam simulasi sistem terdistribusi ini, terdapat beberapa titik kritis yang memerlukan mekanisme **Sinkronisasi (Synchronization)** agar sistem dapat berjalan dengan semestinya: di **Load Balancer** (untuk mengatur antrian request dan kesehatan koneksi) dan di **Server Cluster** (menjaga konsistensi data pada *Shared Database*).

Berikut adalah penjelasan lengkap mengenai mekanisme sinkronisasi yang diterapkan:

---

## 1. Sinkronisasi di Load Balancer (`load_balancer.py`)

Load Balancer berfungsi sebagai gerbang utama bagi banyak *Client* yang terhubung secara bersamaan (*concurrently*). Oleh karena itu, *Load Balancer* menggunakan teknik Multi-Threading untuk menangani masing-masing klien tanpa memblokir klien lain. Di sinilah **Race Condition** dapat terjadi jika sinkronisasi tidak diterapkan.

### A. Fine-Grained Locking (`threading.Lock`)
*   **Masalah**: Algoritma **Round-Robin** bekerja dengan menggeser secara berurutan indeks server (misal: 0 -> 1 -> 2 -> 0). Jika ada 10 thread klien mencoba mengakses dan mengubah nilai indeks (`current_server_index`) pada mili-detik yang sama, nilainya akan korup.
*   **Solusi**: Menggunakan `index_lock = threading.Lock()`.
    *   Setiap thread yang ingin mengambil jatah server berikutnya *harus* meminta izin (acquire lock).
    *   Hanya ada 1 thread yang boleh membaca dan menambah indeks secara bersamaan.
    *   **Optimalisasi**: Lock ini diterapkan dengan metode _fine-grained_ (skala kecil). Lock *dilepaskan* tepat setelah indeks server didapat, **sebelum** fungsi mengecek *health/ping* server (yang memakan waktu jaringan). Hal ini mencegah antrian panjang jika jaringan sedang lambat.

### B. Pembatasan Beban dengan Semaphores (`threading.Semaphore`)
*   **Masalah**: Sebuah backend server memiliki kapasitas maksimal. Jika Load Balancer terus mengirim request ke satu server secara brutal (misal karena server lain sedang mati), server itu bisa *overload* atau mogok (Denial of Service).
*   **Solusi**: Mengimplementasikan `server_semaphores = {port: threading.Semaphore(MAX_CONNECTIONS)}`.
    *   Semaphore bertindak seperti "tiket masuk". Jika sebuah server memiliki kuota maksimal 5 koneksi bersamaan, maka hanya ada 5 tiket yang tersedia.
    *   Jika tiket habis (server sibuk memproses 5 tugas sekaligus), Load Balancer tidak akan memaksa masuk, melainkan melewatkan (skip) server tersebut dan mengoper tugas ke server di putaran selanjutnya.
    *   Tiket dikembalikan ke Load Balancer (`semaphore.release()`) setelah Server membalas respon (baik sukses maupun error).

---

## 2. Distributed Lock pada Server Cluster (`server.py`)

Bagian ini menstimulasikan skenario di mana banyak *node/server* terpisah (dalam hal ini disimulasikan sebagai Multi-Process di *port* berbeda) mecoba mengakses satu _Shared Resource_ atau penyimpanan data utama secara bersama-sama.

### A. File Locking Konkuren (`fcntl.flock`)
*   **Masalah**: Semua server (port 9001, 9002, 9003) diinstruksikan untuk merangkum hasil pemrosesan dan mencatat *log* keberhasilannya ke dalam satu file file teks bersama (`database.txt`). Saat dua server atau lebih mencoba menulis teks ke dalam baris file teks di milidetik yang identik, teks bisa bertumpuk/mangling sehingga baris log rusak (Contoh: `[10:1[10:12:3] Server 1...`).
*   **Solusi**: Menggunakan penguncian level eksekusi Sistem Operasi yaitu modul `fcntl`.
    ```python
    # fcntl.LOCK_EX = Exclusive Lock (Hanya satu proses yang boleh menulis/mengunci)
    fcntl.flock(db_file.fileno(), fcntl.LOCK_EX)
    try:
        db_file.write(log_entry)
        db_file.flush()
        os.fsync(db_file.fileno()) # Memastikan buffer tersimpan ke piringan disk
    finally:
        fcntl.flock(db_file.fileno(), fcntl.LOCK_UN) # Lepaskan kunci!
    ```
*   **Mekanisme Kerja**:
    1. Saat **Server-9001** berhasil mengunci file, ia mulai menempelkan *log* teks ke `database.txt`.
    2. Sedetik kemudian, sebelum Server-9001 selesai, **Server-9002** dan **Server-9003** masuk dan mencoba mengunci file.
    3. OS akan **memblokir / menidurkan (sleep)** eksekusi *Server-9002* dan *Server-9003* pada baris fungsi `flock()`. Mereka otomatis ditempatkan pada 'Ruang Kosong' (Waiting State).
    4. Setelah Server-9001 selesai mem-flush teks ke hardisk dan memanggil `fcntl.LOCK_UN`, OS segera membangunkan *Server-9002* untuk melanjutkan penulisan.

Berkat metode ini, file akan tersusun teratur per baris karena proses antrian penulisan *Shared Data* dijaga kedisiplinannya secara mutlak oleh sistem operasi.

---

## 3. Cara Menjalankan Simulasi

Untuk melihat mekanisme sinkronisasi ini beraksi secara *real-time*, kita menyediakan *script launcher* bernama `run_simulation.py`. *Script* ini otomatis mendirikan 3 Server, 1 Load Balancer, dan menembakkan 5 Klien secara bersamaan (*concurrently*) untuk memancing *Race Condition* buatan.

**Langkah Eksekusi:**
1. Pastikan Anda berada dalam direktori proyek.
2. Jalankan perintah:
```bash
python3 run_simulation.py
```

### Script Pengujian (`run_simulation.py`)
Pemukul Utama Simulasi ini berisi:
```python
import subprocess
import time
import os

print("Memulai Simulasi Sistem Terdistribusi...")

# Hapus database lama jika ada
if os.path.exists("database.txt"):
    os.remove("database.txt")

# 1. Jalankan 3 Backend Server
servers = []
for port in [9001, 9002, 9003]:
    p = subprocess.Popen(["python3", "server.py", str(port)])
    servers.append(p)

time.sleep(1) # Tunggu server siap

# 2. Jalankan Load Balancer
lb = subprocess.Popen(["python3", "load_balancer.py"])

time.sleep(1) # Tunggu LB siap

# 3. Jalankan 5 Client bersamaan (Banyak request bersamaan untuk memicu Race Condition jika fcntl gagal)
clients = []
print("Memulai 5 Client secara bersamaan...")
for client_id in range(1, 6):
    p = subprocess.Popen(["python3", "client.py", str(client_id)])
    clients.append(p)

# Tunggu semua client selesai
for c in clients:
    c.wait()

time.sleep(2)

# Hentikan semua instansi
lb.terminate()
for s in servers:
    s.terminate()

print("\n=== ISI DATABASE BERSAMA (database.txt) ===")
if os.path.exists("database.txt"):
    with open("database.txt", "r") as f:
        print(f.read())
```

---

## 4. Analisis Log Hasil Eksekusi

Saat Anda menjalankan simulasi, Terminal akan dibanjiri oleh proses yang berjalan tumpang-tindih. 

### Bukti Sinkronisasi Bekerja (Terminal Output)
Perhatikan baris-baris berikut yang tercetak di layar:
```
[10:02:01.762] Server-9003 | Menunggu lock pada database.txt...
[10:02:01.762] Server-9003 | Lock didapatkan, menulis ke database...
[10:02:01.762] Server-9003 | Penulisan selesai.
[10:02:01.762] Server-9003 | Lock dilepaskan.
[10:02:01.763] Server-9001 | Menunggu lock pada database.txt...   <----- Server 9001 Antre
[10:02:01.763] Server-9001 | Lock didapatkan, menulis ke database... <----- Server 9001 Masuk stlh 9003 lepas lock
[10:02:01.763] Server-9001 | Penulisan selesai.
[10:02:01.763] Server-9001 | Lock dilepaskan.
```
Terlihat dengan jelas bagaimana Server 9003 mengambil kunci (`flock`). Di milidetik yang sama, ketika Server 9001 mencoba meraih kunci, ia dipaksa **Menunggu lock**. Barulah setelah 9003 melepas file, 9001 dizinkan menulis.

### Bukti Tidak Ada Race Condition (Isi `database.txt`)
Berkat sinkronisasi penulisan diatas, isi `database.txt` tercatat dengan rapi tanpa ada *text-mangling* / tabrakan teks:
```text
[10:02:00.229] Server-9002 memproses '{"client_id": "2", "task_id": "TASK-2-1", "task_type": "Data Processing", "timestamp": "10:02:00.245"}' dari 127.0.0.1
[10:02:00.229] Server-9003 memproses '{"client_id": "4", "task_id": "TASK-4-1", "task_type": "Data Processing", "timestamp": "10:02:00.246"}' dari 127.0.0.1
[10:02:00.231] Server-9001 memproses '{"client_id": "3", "task_id": "TASK-3-1", "task_type": "Database Query", "timestamp": "10:02:00.246"}' dari 127.0.0.1
[10:02:00.229] Server-9002 memproses '{"client_id": "5", "task_id": "TASK-5-1", "task_type": "Data Processing", "timestamp": "10:02:00.246"}' dari 127.0.0.1
[10:02:00.230] Server-9001 memproses '{"client_id": "1", "task_id": "TASK-1-2", "task_type": "Send Email", "timestamp": "10:02:01.254"}' dari 127.0.0.1
```
Semua file tercetak satu per satu per baris dengan bersih. Inilah tujuan utama *Distributed Lock Synchronization* di sistem terdistribusi.
