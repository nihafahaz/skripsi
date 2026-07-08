# Backend Prediksi Harga Cabai (FastAPI + LSTM)

Repository ini merupakan bagian backend dari sistem prediksi harga cabai di Indonesia. Backend dibangun menggunakan **FastAPI** dan memanfaatkan model **LSTM (Long Short-Term Memory)** untuk memprediksi pergerakan harga cabai berdasarkan data historis di 34 provinsi.

---

## 🚀 Fitur Utama
1. **Prediksi Harga (Time-Series Forecasting)**: Memprediksi harga cabai untuk durasi 1, 7, 14, atau 30 hari ke depan menggunakan model LSTM.
2. **API Data Historis**: Mengakses data historis harga cabai yang telah dibersihkan (`data_harga_clean`), difilter berdasarkan provinsi dan jenis cabai.
3. **Data Toko Online**: Menyediakan informasi rekomendasi toko online penyedia cabai dari berbagai platform e-commerce (rating, lokasi, link, dll).
4. **Export PDF Laporan**: Menghasilkan file PDF laporan hasil prediksi secara otomatis menggunakan library `ReportLab`.
5. **Script Ingest Data**: Otomatisasi impor data dari file Excel (`.xlsx`) ke database MySQL.

---

## 🛠️ Tech Stack & Library
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Machine Learning**: TensorFlow (Keras LSTM), NumPy, Joblib (untuk scaling data)
- **Database Connection**: `mysql-connector-python`, `PyMySQL`, `SQLAlchemy`
- **Data Manipulation**: `Pandas`, `openpyxl`
- **PDF Generator**: `ReportLab`
- **Database**: MySQL

---

## 📁 Struktur Folder Penting
- [main.py](file:///c:/Users/Hanifah%20Az-Zahra/AndroidStudioProjects/backend/main.py): Entry point utama backend FastAPI yang berisi seluruh konfigurasi routing endpoint.
- [database.py](file:///c:/Users/Hanifah%20Az-Zahra/AndroidStudioProjects/backend/database.py): Setup koneksi database ke MySQL menggunakan environment variables.
- [import_clean_to_mysql.py](file:///c:/Users/Hanifah%20Az-Zahra/AndroidStudioProjects/backend/import_clean_to_mysql.py): Script pembersih dan pengimpor data excel harga cabai dari folder `clean_data/` ke MySQL.
- [import_toko.py](file:///c:/Users/Hanifah%20Az-Zahra/AndroidStudioProjects/backend/import_toko.py): Script pengimpor data toko online dari file `data_toko_online.xlsx` ke MySQL.
- `models/`: Folder penyimpan file bobot model LSTM trained (`.weights.h5`).
- `scalers/`: Folder penyimpan file scaler data (`.save`) yang digunakan untuk normalisasi input model.

---

## 🔌 API Endpoints

### 1. Root / Health Check
- **Method**: `GET`
- **Path**: `/`
- **Respon**: Konfirmasi backend aktif.

### 2. Dapatkan Data Harga Historis
- **Method**: `GET`
- **Path**: `/harga`
- **Query Params**:
  - `provinsi` (opsional): Nama provinsi (cth: `Sumatera Utara`)
  - `jenis_cabai` (opsional): Jenis cabai (cth: `Cabai Rawit Merah`)
  - `limit` (opsional, default 10): Limit jumlah data.

### 3. Prediksi Harga Cabai
- **Method**: `POST`
- **Path**: `/predict`
- **Request Body (JSON)**:
  ```json
  {
    "provinsi": "Jawa Barat",
    "jenis_cabai": "Cabai Rawit Merah",
    "durasi": 7
  }
  ```
- **Respon**: Data prediksi harga per tanggal beserta perbandingan dengan data aktual jika tersedia.

### 4. Daftar Rekomendasi Toko Online
- **Method**: `GET`
- **Path**: `/toko_online`
- **Respon**: List data toko online cabai (nama toko, platform, harga, rating, link toko, dll).

### 5. Download PDF Laporan Prediksi
- **Method**: `GET`
- **Path**: `/download`
- **Query Params**: `provinsi`, `jenis_cabai`, `durasi`.
- **Respon**: File PDF laporan hasil prediksi untuk diunduh langsung.

---

## ⚙️ Cara Menjalankan Project

### 1. Prasyarat (Prerequisites)
Pastikan Anda sudah menginstal:
- Python 3.10+
- MySQL Server (XAMPP/WampServer)

### 2. Setup Environment & Library
1. Buat virtual environment baru (opsional tapi disarankan):
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Untuk Windows
   ```
2. Instal library pendukung:
   ```bash
   pip install fastapi uvicorn mysql-connector-python pymysql sqlalchemy pandas openpyxl tensorflow numpy reportlab joblib python-dotenv
   ```

### 3. Konfigurasi Database & Environment
1. Buat database baru di MySQL dengan nama `db_cabai`.
2. Buat file `.env` di direktori utama backend dengan isi:
   ```env
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=db_cabai
   ```
3. Pastikan skema tabel `data_harga_clean` dan `toko_online` sudah dibuat.
4. Jalankan script import data Excel ke database:
   ```bash
   python import_clean_to_mysql.py
   python import_toko.py
   ```

### 4. Menjalankan Server FastAPI
Jalankan perintah berikut pada terminal:
```bash
uvicorn main:app --reload
```
Server backend akan aktif secara default di `http://127.0.0.1:8000`.

---

## 📅 Penjadwalan & Otomatisasi Laporan PDF (Auto-Save)
Anda dapat menggunakan script [auto_pdf_generator.py](file:///c:/Users/Hanifah%20Az-Zahra/AndroidStudioProjects/backend/auto_pdf_generator.py) untuk menghasilkan dan menyimpan laporan prediksi PDF secara otomatis ke folder `./laporan_pdf`.

### 1. Menjalankan Sekali (On-Demand / Task Scheduler)
Sangat cocok dipadukan dengan **Windows Task Scheduler** atau **Linux Cron Job** agar berjalan secara berkala:
```bash
# Men-generate PDF untuk seluruh kombinasi provinsi & cabai yang memiliki model
python auto_pdf_generator.py --durasi 7

# Men-generate PDF untuk provinsi atau cabai tertentu saja
python auto_pdf_generator.py --provinsi "Sumatera Utara" --cabai "Cabai Rawit Merah" --durasi 14 --outdir "./laporan_khusus"
```

### 2. Menjalankan Sebagai Background Service (Daemon Loop)
Script akan berjalan terus-menerus di background dan melakukan generate laporan secara otomatis pada waktu yang ditentukan setiap harinya:
```bash
# Otomatis generate setiap hari pukul 08:00 pagi
python auto_pdf_generator.py --scheduler --time "08:00" --durasi 7
```
