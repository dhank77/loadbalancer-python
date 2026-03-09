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
