"""
Script seeding toko online: import data toko dari Excel ke MySQL.

Pengganti import_toko.py dengan struktur yang lebih clean.

Cara penggunaan:
    python scripts/seed_stores.py
    python scripts/seed_stores.py --file /path/ke/data_toko_online.xlsx
"""

import argparse
import os
import sys

import pandas as pd
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.logger import get_logger, setup_logging

logger = get_logger(__name__)

_DEFAULT_EXCEL_FILE = "data_toko_online.xlsx"
_REQUIRED_COLUMNS = [
    "nama_toko", "platform", "nama_produk", "jenis_cabai",
    "harga", "satuan", "lokasi", "rating", "link_toko", "gambar_produk",
]


def _clean_price(nilai) -> int:
    """Bersihkan nilai harga dari format Excel/teks."""
    if pd.isna(nilai):
        return 0
    nilai_str = str(nilai).replace("Rp", "").strip()
    if "." in nilai_str and len(nilai_str.split(".")[-1]) == 1:
        return int(float(nilai_str) * 1000)
    return int(float(nilai_str.replace(".", "").replace(",", "")))


def seed_stores(excel_file: str) -> None:
    """
    Import data toko online dari Excel ke tabel toko_online.

    Args:
        excel_file: Path ke file Excel data toko online.
    """
    if not os.path.exists(excel_file):
        logger.error("File Excel tidak ditemukan: %s", excel_file)
        sys.exit(1)

    df = pd.read_excel(excel_file)
    df.columns = df.columns.str.strip()

    for col in _REQUIRED_COLUMNS:
        if col not in df.columns:
            logger.error("Kolom '%s' tidak ditemukan di Excel.", col)
            sys.exit(1)

    df["harga"] = df["harga"].apply(_clean_price)
    df["rating"] = (
        pd.to_numeric(
            df["rating"].astype(str).str.replace(",", ".").str.strip(),
            errors="coerce",
        ).fillna(0)
    )

    text_cols = [
        "nama_toko", "platform", "nama_produk", "jenis_cabai",
        "satuan", "lokasi", "link_toko", "gambar_produk",
    ]
    df[text_cols] = df[text_cols].fillna("")

    settings = get_settings()
    db_config = {
        "host": settings.db_host,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name,
        "port": settings.db_port,
        "charset": "utf8mb4",
    }

    connection = pymysql.connect(**db_config)
    cursor = connection.cursor()

    sql = """
        INSERT INTO toko_online
        (nama_toko, platform, nama_produk, jenis_cabai, harga, satuan,
         lokasi, rating, link_toko, gambar_toko)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        for _, row in df.iterrows():
            cursor.execute(sql, (
                row["nama_toko"], row["platform"], row["nama_produk"],
                row["jenis_cabai"], int(row["harga"]), row["satuan"],
                row["lokasi"], float(row["rating"]), row["link_toko"],
                row["gambar_produk"],
            ))
        connection.commit()
        logger.info("Berhasil mengimpor %d data toko online.", len(df))
    except Exception as exc:
        connection.rollback()
        logger.error("Gagal mengimpor data toko: %s", exc)
        raise
    finally:
        cursor.close()
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import data toko online ke MySQL.")
    parser.add_argument(
        "--file",
        default=_DEFAULT_EXCEL_FILE,
        help=f"Path ke file Excel (default: {_DEFAULT_EXCEL_FILE}).",
    )
    args = parser.parse_args()

    setup_logging()
    seed_stores(excel_file=args.file)


if __name__ == "__main__":
    main()
