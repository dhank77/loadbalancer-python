# Sistem Distribusi dengan Load Balancer

## Deskripsi

Sistem distribusi sederhana menggunakan **Python Socket Programming** yang mendemonstrasikan konsep **Load Balancing** dengan algoritma **Round-Robin**. Sistem ini terdiri dari 3 komponen utama: Backend Servers, Load Balancer, dan Clients.

---

## Arsitektur Sistem

```
                    ┌─────────────┐
 ┌───────────┐     │             │     ┌──────────────────┐
 │ Client 1  │────▶│             │────▶│ Server 1 (:9001) │
 └───────────┘     │             │     └──────────────────┘
                   │    Load     │
 ┌───────────┐     │  Balancer   │     ┌──────────────────┐
 │ Client 2  │────▶│  (:8000)   │────▶│ Server 2 (:9002) │
 └───────────┘     │             │     └──────────────────┘
                   │ Round-Robin │
 ┌───────────┐     │             │     ┌──────────────────┐
 │ Client 3  │────▶│             │────▶│ Server 3 (:9003) │
 └───────────┘     └─────────────┘     └──────────────────┘
```

### Alur Kerja

1. **Client** mengirim request ke **Load Balancer** (port 8000)
2. **Load Balancer** menerima request dan memilih **Backend Server** menggunakan algoritma **Round-Robin**
3. **Load Balancer** meneruskan (forward) request ke Backend Server yang dipilih
4. **Backend Server** memproses request dan mengirim response ke Load Balancer
5. **Load Balancer** meneruskan response kembali ke Client

---

## Komponen

### 1. Backend Server (`server.py`)

Server backend yang menerima dan memproses request dari Load Balancer.

| Fitur | Keterangan |
|---|---|
| Protocol | TCP Socket |
| Concurrency | Multi-threaded (satu thread per koneksi) |
| Host | `127.0.0.1` |
| Port | Dinamis (diatur via argumen) |

**Cara kerja:**
- Mendengarkan koneksi pada port yang ditentukan
- Setiap koneksi masuk ditangani oleh thread terpisah
- Memproses request dengan delay simulasi (0.1 detik)
- Mengirim response berisi informasi server, request, dan waktu proses

### 2. Load Balancer (`load_balancer.py`)

Komponen inti yang mendistribusikan request dari client ke backend servers.

| Fitur | Keterangan |
|---|---|
| Algoritma | Round-Robin |
| Port | `8000` |
| Backend Servers | 3 server (port 9001, 9002, 9003) |
| Health Check | Ya (skip server yang tidak aktif) |
| Statistik | Menampilkan distribusi saat dihentikan |

**Algoritma Round-Robin:**
```
Request 1  → Server 9001
Request 2  → Server 9002
Request 3  → Server 9003
Request 4  → Server 9001  (kembali ke awal)
Request 5  → Server 9002
...
```

**Health Check:**
- Sebelum meneruskan request, load balancer memeriksa apakah server tujuan aktif
- Jika server tidak aktif, request akan diteruskan ke server berikutnya yang aktif
- Jika semua server tidak aktif, client akan menerima pesan error

### 3. Client (`client.py`)

Client yang mengirim request ke Load Balancer.

| Fitur | Keterangan |
|---|---|
| Target | Load Balancer (`127.0.0.1:8000`) |
| Jumlah Request | 5 request per client |
| Delay | 0.5 detik antar request |
| Timeout | 10 detik per request |

### 4. Runner Script (`run.py`)

Script otomatis untuk menjalankan semua komponen sekaligus.

| Fitur | Keterangan |
|---|---|
| Urutan Start | Servers → Load Balancer → Clients |
| Proses | Subprocess per komponen |
| Cleanup | Ctrl+C menghentikan semua proses |

---

## Cara Menjalankan

### Metode 1: Otomatis (Semua Sekaligus)

```bash
python run.py
```

Script ini akan menjalankan semua komponen secara otomatis:
1. Menjalankan 3 backend servers (port 9001, 9002, 9003)
2. Menjalankan load balancer (port 8000)
3. Menjalankan 3 clients yang mengirim request
4. Tekan **Ctrl+C** untuk menghentikan semua proses

### Metode 2: Manual (Terminal Terpisah)

Buka **7 terminal** dan jalankan perintah berikut:

```bash
# Terminal 1: Server 1
python server.py 9001

# Terminal 2: Server 2
python server.py 9002

# Terminal 3: Server 3
python server.py 9003

# Terminal 4: Load Balancer
python load_balancer.py

# Terminal 5: Client 1
python client.py 1

# Terminal 6: Client 2
python client.py 2

# Terminal 7: Client 3
python client.py 3
```

---

## Contoh Output

### Output Load Balancer

```
============================================================
  LOAD BALANCER - Sistem Distribusi
============================================================
[09:46:00.123] Load Balancer | Berjalan di 127.0.0.1:8000
[09:46:00.123] Load Balancer | Algoritma: Round-Robin
[09:46:00.123] Load Balancer | Backend Servers:
  → 127.0.0.1:9001 [✓ Aktif]
  → 127.0.0.1:9002 [✓ Aktif]
  → 127.0.0.1:9003 [✓ Aktif]

[09:46:01.234] Load Balancer | Request diterima dari ('127.0.0.1', 65182)
[09:46:01.234] Load Balancer | Data: "Client-1 Request #1"
[09:46:01.234] Load Balancer | Meneruskan ke Server-9001 (Round-Robin)
[09:46:01.340] Load Balancer | Response dari Server-9001 diteruskan ke client
```

### Output Client

```
──────────────────────────────────────────────────
  CLIENT-1 - Sistem Distribusi
──────────────────────────────────────────────────
[09:46:01.234] Client-1 | Mengirim: "Client-1 Request #1"
[09:46:01.340] Client-1 | Menerima: "Response dari Server-9001 (port 9001) | ..."

[09:46:03.456] Client-1 | Selesai!
[09:46:03.456] Client-1 | Berhasil: 5/5, Gagal: 0/5
```

### Statistik Distribusi (saat Ctrl+C)

```
============================================================
  STATISTIK DISTRIBUSI LOAD BALANCER
============================================================
  Server-9001:   5 request ( 33.3%) ██████
  Server-9002:   5 request ( 33.3%) ██████
  Server-9003:   5 request ( 33.3%) ██████
  ────────────────────────────────────────
  Total    : 15 request
============================================================
```

---

## Struktur File

```
Distribusi/
├── server.py          # Backend server (multi-threaded)
├── load_balancer.py   # Load balancer (round-robin)
├── client.py          # Client pengirim request
├── run.py             # Runner script (semua sekaligus)
└── README.md          # Dokumentasi ini
```

---

## Teknologi yang Digunakan

| Teknologi | Kegunaan |
|---|---|
| Python `socket` | Komunikasi TCP antar komponen |
| Python `threading` | Menangani multiple koneksi secara concurrent |
| Python `subprocess` | Menjalankan multiple proses di runner script |

---

## Konsep yang Diterapkan

1. **Load Balancing** — Mendistribusikan beban kerja ke beberapa server
2. **Round-Robin** — Algoritma distribusi secara bergantian dan merata
3. **Health Check** — Memeriksa ketersediaan server sebelum meneruskan request
4. **Multi-threading** — Penanganan concurrent connections pada server
5. **Client-Server Architecture** — Arsitektur komunikasi berbasis request-response
6. **TCP Socket Programming** — Komunikasi jaringan menggunakan protokol TCP
# loadbalancer-python
