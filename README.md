# Hangman Multiplayer Game

Game Hangman multiplayer menggunakan HTTP server dan client pygame.

## Fitur
- Menu awal dengan tombol "Buat Kamar" dan "Gabung Kamar"
- Setiap kamar untuk 2 pemain
- Permainan bergantian antar pemain
- Komunikasi menggunakan HTTP requests (GET/POST)
- **Kata yang ditebak: Nama-nama merk mobil**
- **Clue/petunjuk untuk setiap kata**
- **Visualisasi hangman yang benar (urutan: platform → tiang → balok → tali → kepala → badan)**
- Feedback visual untuk setiap tebakan
- Game state yang real-time

## Struktur File
- `server_thread_http.py` - HTTP server threading
- `http.py` - HTTP handler dengan implementasi game logic
- `hangman_client.py` - Client pygame untuk UI game
- `start_server.bat` - Script untuk menjalankan server
- `start_client.bat` - Script untuk menjalankan client

## Prerequisites
Pastikan Python sudah terinstall, kemudian install pygame:
```
pip install pygame
```

Atau gunakan requirements.txt:
```
pip install -r requirements.txt
```

## Cara Menjalankan

### 1. Menjalankan Server
```
python server_thread_http.py
```
Atau double-click `start_server.bat`

Server akan berjalan di `localhost:8889`

### 2. Menjalankan Client
```
python hangman_client.py
```
Atau double-click `start_client.bat`

## Cara Bermain

### Menu Utama
1. **Create Room** - Membuat room baru dan otomatis menjadi Player 1, menunggu Player 2
2. **Join Room** - Melihat daftar room yang tersedia dan bergabung sebagai Player 2

### Gameplay
1. Player 1 membuat room dan langsung masuk sebagai pemain pertama
2. Player 2 bergabung ke room yang tersedia
3. Setelah 2 pemain bergabung, game akan otomatis dimulai
4. Pemain akan melihat **clue/petunjuk** tentang merk mobil yang harus ditebak
5. Pemain bergantian menebak huruf (dimulai dari Player 1)
6. Tekan huruf di keyboard untuk menebak
7. Feedback akan diberikan apakah huruf benar atau salah
8. Hangman akan digambar dengan urutan yang benar: platform → tiang → balok horizontal → tali gantung → kepala → badan
9. Game berakhir ketika:
   - Kata berhasil ditebak (pemain yang menebak menang)
   - Hangman selesai digambar setelah 6 kesalahan (kedua pemain kalah)

## Endpoints HTTP

### GET Endpoints
- `GET /` - Main menu HTML
- `GET /rooms` - Daftar semua room
- `GET /room/{room_id}` - Status room tertentu

### POST Endpoints
- `POST /create_room` - Membuat room baru
- `POST /join/{room_id}` - Bergabung ke room
- `POST /guess/{room_id}/{letter}` - Menebak huruf

## Game Logic
- Setiap game menggunakan **nama merk mobil** random dari 15 pilihan yang tersedia
- **Setiap kata disertai dengan clue/petunjuk** yang membantu pemain menebak
- Maksimal **6 kesalahan** sebelum hangman selesai (urutan: platform → tiang → balok → tali → kepala → badan)
- Pemain bergantian setiap kali menebak (benar atau salah)
- Game state disimpan di server dan disinkronisasi ke semua client
- **Feedback real-time** untuk setiap tebakan (benar/salah/sudah ditebak)

## Daftar Merk Mobil yang Tersedia
- TOYOTA, HONDA, FERRARI, BMW, MERCEDES
- LAMBORGHINI, PORSCHE, AUDI, NISSAN, HYUNDAI  
- MAZDA, VOLKSWAGEN, FORD, CHEVROLET, MITSUBISHI

Setiap merk disertai dengan clue yang membantu pemain menebak!

## Troubleshooting

### Error: Import "pygame" could not be resolved
Install pygame: `pip install pygame`

### Error: Connection refused
Pastikan server sudah berjalan di port 8889

### Error: Room not found
Refresh daftar room atau buat room baru
