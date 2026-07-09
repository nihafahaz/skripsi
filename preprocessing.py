import os
import numpy as np
import pandas as pd
from database import get_db_connection

# =========================================================
# KONFIGURASI
# =========================================================

FOLDER_CLEAN = "clean_data"

PROVINSI_LIST = [
    'Aceh', 'Bali', 'Banten', 'Bengkulu', 'DI Yogyakarta', 'DKI Jakarta',
    'Gorontalo', 'Jambi', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur',
    'Kalimantan Barat', 'Kalimantan Selatan', 'Kalimantan Tengah',
    'Kalimantan Timur', 'Kalimantan Utara', 'Kepulauan Bangka Belitung',
    'Kepulauan Riau', 'Lampung', 'Maluku', 'Maluku Utara',
    'Nusa Tenggara Barat', 'Nusa Tenggara Timur', 'Papua', 'Papua Barat',
    'Riau', 'Sulawesi Barat', 'Sulawesi Selatan', 'Sulawesi Tengah',
    'Sulawesi Tenggara', 'Sulawesi Utara', 'Sumatera Barat',
    'Sumatera Selatan', 'Sumatera Utara'
]

JENIS_CABAI_LIST = [
    'Cabai Merah Besar',
    'Cabai Merah Keriting',
    'Cabai Rawit Merah',
    'Cabai Rawit Hijau'
]


def bersihkan_harga(nilai):
    """Membersihkan nilai harga dari karakter non-numerik."""
    if pd.isna(nilai):
        return None

    nilai = str(nilai).strip()

    if nilai in ["", "-", "nan", "None"]:
        return None

    nilai = nilai.replace(",", "")
    nilai = nilai.replace(".", "")

    return pd.to_numeric(nilai, errors="coerce")


def interpolasi_missing_value(data, provinsi, jenis):
    """
    Mengisi missing value menggunakan interpolasi.
    Mengacu pada skripsi_lstm.ipynb:
    - Default: spline order 3
    - Fallback: linear limit_direction='both'
    - Khusus Gorontalo + Cabai Rawit Hijau: langsung linear
    """

    if (provinsi, jenis) == ("Gorontalo", "Cabai Rawit Hijau"):
        data["harga"] = data["harga"].interpolate(
            method="linear",
            limit_direction="both"
        )
    else:
        try:
            data["harga"] = data["harga"].interpolate(
                method="spline",
                order=3
            )
        except Exception:
            data["harga"] = data["harga"].interpolate(
                method="linear",
                limit_direction="both"
            )

    # Isi sisa NaN di ujung data
    data["harga"] = data["harga"].bfill().ffill()

    return data


def main():
    print("[*] Memulai proses preprocessing...")

    os.makedirs(FOLDER_CLEAN, exist_ok=True)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    total_diproses = 0

    for provinsi in PROVINSI_LIST:
        for jenis in JENIS_CABAI_LIST:

            # Ambil data dari database
            cursor.execute(
                """
                SELECT id, tanggal, harga
                FROM data_harga_clean
                WHERE provinsi = %s AND jenis_cabai = %s
                ORDER BY tanggal ASC
                """,
                (provinsi, jenis)
            )

            rows = cursor.fetchall()

            if len(rows) == 0:
                print(f"  [!] Tidak ada data untuk: {provinsi} - {jenis} (skip)")
                continue

            # Buat DataFrame
            data = pd.DataFrame(rows)
            data["tanggal"] = pd.to_datetime(data["tanggal"])
            data = data.sort_values("tanggal").reset_index(drop=True)

            # Bersihkan harga
            data["harga"] = data["harga"].apply(bersihkan_harga)

            # Hitung missing value sebelum interpolasi
            missing_sebelum = data["harga"].isna().sum()

            if missing_sebelum == 0:
                print(f"  [✓] {provinsi} - {jenis}: tidak ada missing value")
            else:
                print(f"  [~] {provinsi} - {jenis}: {missing_sebelum} missing value → interpolasi...")

                # Interpolasi missing value
                data = interpolasi_missing_value(data, provinsi, jenis)

            # Pembulatan harga: (harga / 100).round() * 100
            data["harga"] = (data["harga"] / 100).round() * 100
            data["harga"] = data["harga"].astype(int)

            # =====================================================
            # SIMPAN KE FILE EXCEL (clean_data/)
            # =====================================================

            nama_file = f"{provinsi}_{jenis}.xlsx"
            output_path = os.path.join(FOLDER_CLEAN, nama_file)

            df_export = data[["tanggal", "harga"]].copy()
            df_export = df_export.rename(columns={"tanggal": "date"})
            df_export.to_excel(output_path, index=False)

            # =====================================================
            # UPDATE HARGA DI DATABASE
            # =====================================================

            for _, row in data.iterrows():
                cursor.execute(
                    """
                    UPDATE data_harga_clean
                    SET harga = %s
                    WHERE id = %s
                    """,
                    (int(row["harga"]), int(row["id"]))
                )

            total_diproses += 1

    connection.commit()
    cursor.close()
    connection.close()

    print(f"\n[+] Preprocessing selesai! {total_diproses} kombinasi diproses.")
    print(f"[+] File clean disimpan ke folder: {FOLDER_CLEAN}/")


if __name__ == "__main__":
    main()
