import os
import numpy as np
import pandas as pd
from database import get_db_connection
from datetime import datetime, timedelta

# =========================================================
# KONFIGURASI
# =========================================================

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

# Pasangan jenis cabai yang saling mengikuti pola
PASANGAN_CABAI = {
    'Cabai Rawit Hijau': 'Cabai Rawit Merah',
    'Cabai Rawit Merah': 'Cabai Rawit Hijau',
    'Cabai Merah Keriting': 'Cabai Merah Besar',
    'Cabai Merah Besar': 'Cabai Merah Keriting',
}

MAX_BARIS = 800


def ambil_rata_rata_nasional(cursor, jenis_cabai):
    """Ambil rata-rata harga nasional untuk jenis cabai tertentu."""
    cursor.execute(
        """
        SELECT AVG(harga) as rata_rata
        FROM data_harga_clean
        WHERE jenis_cabai = %s AND harga IS NOT NULL
        """,
        (jenis_cabai,)
    )
    result = cursor.fetchone()
    rata = result["rata_rata"]

    if rata is None:
        # Fallback default harga per jenis cabai
        default = {
            'Cabai Merah Besar': 45000,
            'Cabai Merah Keriting': 48000,
            'Cabai Rawit Merah': 55000,
            'Cabai Rawit Hijau': 40000,
        }
        return default.get(jenis_cabai, 45000)

    return float(rata)


def ambil_data_pasangan(cursor, provinsi, jenis_pasangan):
    """
    Ambil data harga dari jenis cabai pasangan di provinsi yang sama.
    Contoh: Rawit Hijau mengikuti pola Rawit Merah di provinsi yang sama.
    """
    cursor.execute(
        """
        SELECT tanggal, harga
        FROM data_harga_clean
        WHERE provinsi = %s AND jenis_cabai = %s AND harga IS NOT NULL
        ORDER BY tanggal ASC
        """,
        (provinsi, jenis_pasangan)
    )
    rows = cursor.fetchall()

    if len(rows) == 0:
        return None

    df = pd.DataFrame(rows)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["harga"] = df["harga"].astype(float)
    return df


def generate_dari_pola_pasangan(df_pasangan, rata_rata_target, target_rows):
    """
    Generate harga berdasarkan pola naik-turun dari jenis cabai pasangan,
    di-scale ke rata-rata nasional dari jenis cabai target.
    """
    harga_pasangan = df_pasangan["harga"].values

    # Ambil sebanyak target_rows terakhir (atau semua kalau < target_rows)
    if len(harga_pasangan) > target_rows:
        harga_pasangan = harga_pasangan[-target_rows:]

    # Hitung pola perubahan relatif (naik/turun) dari pasangan
    rata_pasangan = np.mean(harga_pasangan)

    if rata_pasangan == 0:
        rata_pasangan = 1

    # Normalisasi pola: perubahan relatif terhadap rata-rata pasangan
    pola_relatif = harga_pasangan / rata_pasangan

    # Terapkan pola ke rata-rata target
    harga_generated = pola_relatif * rata_rata_target

    # Tambah sedikit noise agar tidak identik
    np.random.seed(42)
    noise = np.random.normal(0, rata_rata_target * 0.02, len(harga_generated))
    harga_generated = harga_generated + noise

    # Pastikan harga tidak negatif
    harga_generated = np.maximum(harga_generated, 1000)

    # Kalau data pasangan lebih sedikit dari target, ulangi pola
    if len(harga_generated) < target_rows:
        pengulangan = int(np.ceil(target_rows / len(harga_generated)))
        harga_generated = np.tile(harga_generated, pengulangan)[:target_rows]

    return harga_generated


def generate_dari_rata_rata_saja(rata_rata, target_rows):
    """
    Fallback: generate harga dari rata-rata nasional saja
    dengan pola naik-turun sinusoidal + noise.
    """
    np.random.seed(42)

    # Trend ringan naik
    trend = np.linspace(rata_rata * 0.95, rata_rata * 1.05, target_rows)

    # Pola musiman 30 hari
    seasonal = (rata_rata * 0.08) * np.sin(
        np.arange(target_rows) * 2 * np.pi / 30
    )

    # Noise random
    noise = np.random.normal(0, rata_rata * 0.03, target_rows)

    harga = trend + seasonal + noise
    harga = np.maximum(harga, 1000)

    return harga


def main():
    print("[*] Memulai proses data synthesis...")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Hitung range tanggal
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=MAX_BARIS - 1)

    inserted_count = 0

    for provinsi in PROVINSI_LIST:
        for jenis in JENIS_CABAI_LIST:

            # Cek apakah kombinasi ini sudah punya data
            cursor.execute(
                """
                SELECT COUNT(*) as jumlah
                FROM data_harga_clean
                WHERE provinsi = %s AND jenis_cabai = %s
                """,
                (provinsi, jenis)
            )
            result = cursor.fetchone()
            jumlah = result["jumlah"]

            if jumlah > 0:
                continue

            # =================================================
            # DATA KOSONG 100% → GENERATE HARGA
            # =================================================

            print(f"  [+] Generate data untuk: {provinsi} - {jenis}")

            # 1. Ambil rata-rata nasional untuk jenis cabai ini
            rata_rata = ambil_rata_rata_nasional(cursor, jenis)

            # 2. Coba ambil pola dari jenis cabai pasangan
            #    (Rawit Hijau ↔ Rawit Merah, Merah Keriting ↔ Merah Besar)
            jenis_pasangan = PASANGAN_CABAI[jenis]
            df_pasangan = ambil_data_pasangan(cursor, provinsi, jenis_pasangan)

            if df_pasangan is not None and len(df_pasangan) >= 10:
                # Ada data pasangan → generate berdasarkan pola pasangan
                print(f"      Mengikuti pola: {jenis_pasangan} ({len(df_pasangan)} data)")
                harga_array = generate_dari_pola_pasangan(
                    df_pasangan, rata_rata, MAX_BARIS
                )
            else:
                # Tidak ada data pasangan → fallback rata-rata + sinusoidal
                print(f"      Fallback: rata-rata nasional ({rata_rata:.0f})")
                harga_array = generate_dari_rata_rata_saja(rata_rata, MAX_BARIS)

            # 3. Pembulatan harga
            harga_array = (np.array(harga_array) / 100).round() * 100
            harga_array = harga_array.astype(int)

            # 4. Insert ke database
            for i in range(MAX_BARIS):
                tanggal = start_date + timedelta(days=i)

                cursor.execute(
                    """
                    INSERT INTO data_harga_clean (tanggal, provinsi, jenis_cabai, harga)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tanggal, provinsi, jenis, int(harga_array[i]))
                )

            inserted_count += 1

    connection.commit()

    # =================================================
    # FASE 2: GANTI BARIS KOSONG (NULL) MENJADI NaN
    # Untuk data yang sudah ada tapi punya gap/hole
    # =================================================

    print("\n[*] Mengecek baris kosong (harga NULL) di database...")

    cursor.execute(
        """
        SELECT COUNT(*) as jumlah_null
        FROM data_harga_clean
        WHERE harga IS NULL
        """
    )
    result = cursor.fetchone()
    jumlah_null = result["jumlah_null"]

    if jumlah_null > 0:
        print(f"  [!] Ditemukan {jumlah_null} baris dengan harga NULL")
        print(f"      Baris-baris ini akan diisi oleh preprocessing (interpolasi)")
    else:
        print("  [✓] Tidak ada baris kosong di database")

    cursor.close()
    connection.close()

    if inserted_count == 0:
        print("\n[*] Semua kombinasi sudah terisi. Tidak ada data yang di-generate.")
    else:
        print(f"\n[+] Selesai! {inserted_count} kombinasi baru di-generate ({MAX_BARIS} baris masing-masing).")


if __name__ == "__main__":
    main()
