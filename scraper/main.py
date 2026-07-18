"""
Entry point scraper BI PIHPS.

Mengorkestrasikan seluruh proses scraping:
1. Jalankan live scraping via Selenium
2. Jika gagal atau kosong → gunakan fallback generator
3. Simpan ke database MySQL
"""

import sys
import os

# Pastikan root project ada di sys.path saat dijalankan langsung
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logger import get_logger, setup_logging
from scraper.engine import run_live_scraping
from scraper.fallback import generate_fallback_data
from scraper.repository import save_records

logger = get_logger(__name__)


def main() -> None:
    """
    Jalankan pipeline scraping lengkap.

    Urutan eksekusi:
    1. Live scraping → parse → validasi
    2. Fallback (jika scraping gagal atau tidak ada hasil)
    3. Simpan ke database
    """
    setup_logging()
    logger.info("Memulai Scraper BI PIHPS...")

    records: list[dict] = []

    # --- Live scraping ---
    try:
        records = run_live_scraping()
    except Exception as exc:
        logger.warning("Live scraping gagal: %s", exc)

    # --- Fallback jika kosong ---
    if not records:
        records = generate_fallback_data()

    # --- Simpan ke database ---
    if records:
        result = save_records(records)
        logger.info(
            "Scraping selesai: %d inserted, %d updated.",
            result["inserted"],
            result["updated"],
        )
    else:
        logger.warning("Tidak ada record yang berhasil dikumpulkan.")


if __name__ == "__main__":
    main()
