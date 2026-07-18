"""
Script data synthesis: generate data harga sintetis untuk kombinasi yang kosong.

Pengganti data_synthesis.py dengan struktur yang lebih clean.

Cara penggunaan:
    python scripts/synthesize_data.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.logger import get_logger, setup_logging
from app.db.session import get_db_connection
from app.utils.constants import JENIS_CABAI_LIST, PASANGAN_CABAI, PROVINSI_LIST

logger = get_logger(__name__)

# Harga default fallback per jenis cabai (rupiah)
_DEFAULT_PRICES: dict[str, int] = {
    "Cabai Merah Besar": 45_000,
    "Cabai Merah Keriting": 48_000,
    "Cabai Rawit Merah": 55_000,
    "Cabai Rawit Hijau": 40_000,
}


def _get_national_average(cursor, jenis_cabai: str) -> float:
    cursor.execute(
        """
        SELECT AVG(harga) AS rata_rata FROM data_harga_clean
        WHERE jenis_cabai = %s AND harga IS NOT NULL
        """,
        (jenis_cabai,),
    )
    result = cursor.fetchone()
    rata = result["rata_rata"] if result else None
    return float(rata) if rata else float(_DEFAULT_PRICES.get(jenis_cabai, 45_000))


def _get_paired_data(cursor, provinsi: str, jenis_pasangan: str) -> pd.DataFrame | None:
    cursor.execute(
        """
        SELECT tanggal, harga FROM data_harga_clean
        WHERE provinsi = %s AND jenis_cabai = %s AND harga IS NOT NULL
        ORDER BY tanggal ASC
        """,
        (provinsi, jenis_pasangan),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["harga"] = df["harga"].astype(float)
    return df


def _generate_from_pair(df_pair: pd.DataFrame, target_avg: float, n: int) -> np.ndarray:
    prices = df_pair["harga"].values
    if len(prices) > n:
        prices = prices[-n:]
    avg_pair = np.mean(prices) or 1.0
    pattern = prices / avg_pair
    result = pattern * target_avg
    np.random.seed(42)
    result += np.random.normal(0, target_avg * 0.02, len(result))
    result = np.maximum(result, 1_000)
    if len(result) < n:
        repeats = int(np.ceil(n / len(result)))
        result = np.tile(result, repeats)[:n]
    return result


def _generate_from_average(avg: float, n: int) -> np.ndarray:
    np.random.seed(42)
    trend = np.linspace(avg * 0.95, avg * 1.05, n)
    seasonal = (avg * 0.08) * np.sin(np.arange(n) * 2 * np.pi / 30)
    noise = np.random.normal(0, avg * 0.03, n)
    return np.maximum(trend + seasonal + noise, 1_000)


def synthesize_data() -> None:
    """Generate dan insert data sintetis untuk kombinasi yang belum ada datanya."""
    settings = get_settings()
    max_rows = settings.synthesis_max_rows

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=max_rows - 1)

    inserted_count = 0

    for provinsi in PROVINSI_LIST:
        for jenis in JENIS_CABAI_LIST:
            cursor.execute(
                "SELECT COUNT(*) AS jumlah FROM data_harga_clean "
                "WHERE provinsi = %s AND jenis_cabai = %s",
                (provinsi, jenis),
            )
            if cursor.fetchone()["jumlah"] > 0:
                continue

            logger.info("Generate data: %s / %s", provinsi, jenis)

            avg = _get_national_average(cursor, jenis)
            jenis_pasangan = PASANGAN_CABAI.get(jenis)
            df_pair = (
                _get_paired_data(cursor, provinsi, jenis_pasangan)
                if jenis_pasangan
                else None
            )

            if df_pair is not None and len(df_pair) >= 10:
                prices = _generate_from_pair(df_pair, avg, max_rows)
            else:
                prices = _generate_from_average(avg, max_rows)

            prices = ((np.array(prices) / 100).round() * 100).astype(int)

            for i in range(max_rows):
                tanggal = start_date + timedelta(days=i)
                cursor.execute(
                    """
                    INSERT INTO data_harga_clean (tanggal, provinsi, jenis_cabai, harga)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tanggal, provinsi, jenis, int(prices[i])),
                )

            inserted_count += 1

    connection.commit()
    cursor.close()
    connection.close()

    if inserted_count == 0:
        logger.info("Semua kombinasi sudah terisi. Tidak ada data yang di-generate.")
    else:
        logger.info(
            "Selesai! %d kombinasi baru di-generate (%d baris masing-masing).",
            inserted_count, max_rows,
        )


if __name__ == "__main__":
    setup_logging()
    synthesize_data()
