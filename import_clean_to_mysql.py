import os
import pandas as pd
from sqlalchemy import create_engine

# folder tempat file clean kamu
folder_clean = "clean_data"

# koneksi MySQL dari env
db_host = os.getenv("DB_HOST", "localhost")
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASSWORD", "")
db_name = os.getenv("DB_NAME", "db_cabai")

engine = create_engine(f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}")

with engine.begin() as conn:
    conn.exec_driver_sql("TRUNCATE TABLE data_harga_clean")

for file in os.listdir(folder_clean):
    if not file.endswith(".xlsx"):
        continue

    path = os.path.join(folder_clean, file)

    # ambil provinsi dan jenis dari nama file
    # contoh: Sumatera Utara_Cabai Rawit Merah.xlsx
    nama = os.path.splitext(file)[0]
    provinsi, jenis = nama.split("_", 1)

    data = pd.read_excel(path)

    # samakan nama kolom
    data = data.rename(columns={
        "date": "tanggal",
        "harga": "harga"
    })

    # ambil kolom yang dibutuhkan saja
    data = data[["tanggal", "harga"]]

    # tambah kolom provinsi dan jenis cabai
    data["provinsi"] = provinsi
    data["jenis_cabai"] = jenis

    # rapikan tipe data
    data["tanggal"] = pd.to_datetime(data["tanggal"]).dt.date
    data["harga"] = data["harga"].round(0).astype(int)

    # urutkan kolom sesuai tabel MySQL
    data = data[["tanggal", "provinsi", "jenis_cabai", "harga"]]

    # masukkan ke MySQL
    data.to_sql(
        "data_harga_clean",
        con=engine,
        if_exists="append",
        index=False
    )

    print(f"Berhasil import: {file}")

print("Semua data clean berhasil dimasukkan ke MySQL.")