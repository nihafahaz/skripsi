import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# Database connection details from .env
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

print(f"[*] Menghubungkan ke Aiven Database: {DB_HOST}:{DB_PORT}...")

# Struktur tabel (DDL) untuk Aiven MySQL
queries = [
    """
    CREATE TABLE IF NOT EXISTS data_harga_clean (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tanggal DATE,
        provinsi VARCHAR(100),
        jenis_cabai VARCHAR(100),
        harga INT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS toko_online (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nama_toko VARCHAR(255),
        platform VARCHAR(100),
        nama_produk VARCHAR(255),
        jenis_cabai VARCHAR(100),
        harga INT,
        satuan VARCHAR(50),
        lokasi VARCHAR(100),
        rating FLOAT,
        link_toko TEXT,
        gambar_toko TEXT
    );
    """
]

try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )
    cursor = conn.cursor()
    
    for q in queries:
        cursor.execute(q)
        print("[+] Tabel berhasil dibuat atau sudah ada.")
        
    conn.commit()
    cursor.close()
    conn.close()
    print("[OK] Inisialisasi Database Aiven Berhasil Selesai!")
except Exception as e:
    print(f"[-] Terjadi kesalahan: {e}")
