"""
Fallback generator — data simulasi jika live scraping gagal.

Membangkitkan data harga sintetis untuk 3 hari terakhir
ketika website BI PIHPS tidak dapat diakses (down / diblokir).
"""

import datetime
import random

from app.core.logger import get_logger
from app.utils.constants import JENIS_CABAI_LIST, PROVINSI_LIST

logger = get_logger(__name__)

# Rentang harga realistis per jenis cabai (min, max) dalam rupiah
_PRICE_RANGES: dict[str, tuple[int, int]] = {
    "Cabai Merah Besar": (30_000, 55_000),
    "Cabai Merah Keriting": (35_000, 60_000),
    "Cabai Rawit Merah": (40_000, 80_000),
    "Cabai Rawit Hijau": (30_000, 50_000),
}

_FALLBACK_DAYS: int = 3  # Simulasikan N hari terakhir


def generate_fallback_data() -> list[dict]:
    """
    Generate data harga simulasi untuk semua kombinasi provinsi dan jenis cabai
    selama 3 hari terakhir.

    Data ini digunakan sebagai pengganti sementara ketika live scraping gagal.

    Returns:
        List dict dengan kunci 'tanggal', 'provinsi', 'jenis_cabai', 'harga'.
    """
    logger.warning(
        "Live scraping gagal. Mengaktifkan fallback generator untuk %d hari terakhir.",
        _FALLBACK_DAYS,
    )

    today = datetime.date.today()
    records: list[dict] = []

    for offset in range(_FALLBACK_DAYS):
        tanggal = (today - datetime.timedelta(days=offset)).strftime("%Y-%m-%d")
        for prov in PROVINSI_LIST:
            for jenis in JENIS_CABAI_LIST:
                min_price, max_price = _PRICE_RANGES.get(
                    jenis, (30_000, 60_000)
                )
                records.append({
                    "tanggal": tanggal,
                    "provinsi": prov,
                    "jenis_cabai": jenis,
                    "harga": random.randint(min_price, max_price),
                })

    logger.info(
        "Fallback menghasilkan %d record simulasi.", len(records)
    )
    return records
