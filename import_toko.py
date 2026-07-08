import pandas as pd
import pymysql

# =========================
# KONFIGURASI
# =========================
file_excel = "data_toko_online.xlsx"

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "db_cabai",  # ganti sesuai nama database kamu
    "charset": "utf8mb4"
}

# =========================
# BACA FILE EXCEL
# =========================
df = pd.read_excel(file_excel)

# Rapikan nama kolom jika ada spasi tidak sengaja
df.columns = df.columns.str.strip()

# Pastikan kolom sesuai
required_columns = [
    "nama_toko",
    "platform",
    "nama_produk",
    "jenis_cabai",
    "harga",
    "satuan",
    "lokasi",
    "rating",
    "link_toko",
    "gambar_produk"
]

for col in required_columns:
    if col not in df.columns:
        raise Exception(f"Kolom '{col}' tidak ditemukan di Excel.")

# Bersihkan data harga
def bersihkan_harga(nilai):
    if pd.isna(nilai):
        return 0

    nilai = str(nilai).replace("Rp", "").strip()

    # Kalau dari Excel kebaca 25.0 / 50.9, artinya ribuan
    if "." in nilai and len(nilai.split(".")[-1]) == 1:
        return int(float(nilai) * 1000)

    # Kalau formatnya 25.000 atau 50.900
    nilai = nilai.replace(".", "").replace(",", "")

    return int(float(nilai))


df["harga"] = df["harga"].apply(bersihkan_harga)

# Bersihkan rating
df["rating"] = (
    df["rating"]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .str.strip()
)

df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0)

# Kosongkan NaN di kolom teks
text_columns = [
    "nama_toko",
    "platform",
    "nama_produk",
    "jenis_cabai",
    "satuan",
    "lokasi",
    "link_toko",
    "gambar_produk"
]

df[text_columns] = df[text_columns].fillna("")

# =========================
# MASUKKAN KE DATABASE
# =========================
connection = pymysql.connect(**db_config)
cursor = connection.cursor()

sql = """
INSERT INTO toko_online
(nama_toko, platform, nama_produk, jenis_cabai, harga, satuan, lokasi, rating, link_toko, gambar_produk)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

try:
    for _, row in df.iterrows():
        values = (
            row["nama_toko"],
            row["platform"],
            row["nama_produk"],
            row["jenis_cabai"],
            int(row["harga"]),
            row["satuan"],
            row["lokasi"],
            float(row["rating"]),
            row["link_toko"],
            row["gambar_produk"]
        )

        cursor.execute(sql, values)

    connection.commit()
    print(f"Berhasil memasukkan {len(df)} data ke tabel toko_online.")

except Exception as e:
    connection.rollback()
    print("Terjadi error:", e)

finally:
    cursor.close()
    connection.close()