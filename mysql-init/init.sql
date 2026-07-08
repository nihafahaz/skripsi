CREATE DATABASE IF NOT EXISTS db_cabai;
USE db_cabai;

-- Tabel data_harga_clean
CREATE TABLE IF NOT EXISTS data_harga_clean (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tanggal DATE,
    provinsi VARCHAR(100),
    jenis_cabai VARCHAR(100),
    harga INT
);

-- Tabel toko_online
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
