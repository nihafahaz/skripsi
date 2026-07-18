"""
Script seeding database: import data harga historis dari file Excel ke MySQL.

Digunakan sekali saat inisialisasi database pertama kali.
Data diambil dari folder yang berisi file Excel dengan format:
    {Provinsi}_{Jenis Cabai}.xlsx

Setiap file Excel harus memiliki kolom: tanggal (atau date), harga.

Cara penggunaan:
    python scripts/seed_database.py --data-dir /path/ke/folder/excel
"""

import argparse
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

# Tambah root project ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.logger import get_logger, setup_logging

logger = get_logger(__name__)


def seed_database(data_dir: str, truncate: bool = False) -> None:
    """
    Import data harga dari folder Excel ke tabel data_harga_clean.

    Args:
        data_dir: Path ke folder yang berisi file Excel.
        truncate: Jika True, kosongkan tabel sebelum import.
    """
    settings = get_settings()
    engine = create_engine(settings.db_url)

    if not os.path.isdir(data_dir):
        logger.error("Folder data tidak ditemukan: %s", data_dir)
        sys.exit(1)

    if truncate:
        logger.warning("Mengosongkan tabel data_harga_clean...")
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE data_harga_clean"))

    excel_files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
    if not excel_files:
        logger.warning("Tidak ada file .xlsx ditemukan di: %s", data_dir)
        return

    total_rows = 0

    for filename in excel_files:
        filepath = os.path.join(data_dir, filename)
        name_no_ext = os.path.splitext(filename)[0]

        try:
            provinsi, jenis = name_no_ext.split("_", 1)
        except ValueError:
            logger.warning("Format nama file tidak valid, skip: %s", filename)
            continue

        try:
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.strip()

            # Normalisasi nama kolom tanggal
            if "date" in df.columns:
                df = df.rename(columns={"date": "tanggal"})

            df = df[["tanggal", "harga"]].copy()
            df["provinsi"] = provinsi
            df["jenis_cabai"] = jenis
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
            df["harga"] = df["harga"].round(0).astype(int)
            df = df[["tanggal", "provinsi", "jenis_cabai", "harga"]]

            df.to_sql(
                "data_harga_clean",
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
            )

            total_rows += len(df)
            logger.info("[OK] %s — %d baris", filename, len(df))

        except Exception as exc:
            logger.error("[GAGAL] %s: %s", filename, exc)
            continue

    logger.info("Seeding selesai. Total %d baris diimpor.", total_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import data harga Excel ke database MySQL."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Path ke folder berisi file Excel.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Kosongkan tabel sebelum import.",
    )
    args = parser.parse_args()

    setup_logging()
    seed_database(data_dir=args.data_dir, truncate=args.truncate)


if __name__ == "__main__":
    main()
