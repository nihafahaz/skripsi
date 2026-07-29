"""
Scheduler otomatis untuk BI PIHPS Scraper.

Menjalankan pipeline scraping setiap hari pukul 06:00 WIB (UTC+7).
Service ini berjalan terus-menerus (restart: always) di dalam Docker.

Cara kerja:
- Saat pertama kali dijalankan → langsung scraping sekali
- Selanjutnya → scraping dijadwalkan setiap hari pukul 06:00 WIB
"""

import sys
import os
import time
import schedule
import datetime

# Pastikan root project ada di sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logger import get_logger, setup_logging
from scraper.engine import run_live_scraping
from scraper.fallback import generate_fallback_data
from scraper.repository import save_records

logger = get_logger(__name__)

# Waktu scraping harian (WIB = UTC+7, di container timezone UTC → jam 23:00 UTC)
_SCHEDULE_TIME_UTC = "23:00"   # = 06:00 WIB
_SCHEDULE_TIME_LABEL = "06:00 WIB"


def run_scraping_job() -> None:
    """
    Satu siklus pipeline scraping lengkap.

    Dipanggil oleh scheduler maupun saat startup awal.
    """
    now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    logger.info(
        "========================================================"
    )
    logger.info(
        "Memulai scraping terjadwal — %s WIB",
        now_wib.strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info(
        "========================================================"
    )

    records: list[dict] = []

    # Live scraping
    try:
        records = run_live_scraping()
    except Exception as exc:
        logger.warning("Live scraping gagal: %s", exc)

    # Fallback jika kosong
    if not records:
        records = generate_fallback_data()

    # Simpan ke database
    if records:
        result = save_records(records)
        logger.info(
            "Scraping selesai: %d inserted, %d updated.",
            result["inserted"],
            result["updated"],
        )
    else:
        logger.warning("Tidak ada record yang berhasil dikumpulkan.")


def main() -> None:
    """
    Entry point scheduler.

    1. Setup logging
    2. Jalankan scraping langsung sekali saat startup
    3. Jadwalkan scraping harian pukul 06:00 WIB
    4. Loop selamanya
    """
    setup_logging()
    logger.info("Scraper Scheduler dimulai.")
    logger.info("Jadwal: setiap hari pukul %s", _SCHEDULE_TIME_LABEL)

    # Jalankan sekali saat startup agar data langsung tersedia
    logger.info("Menjalankan scraping awal saat startup...")
    run_scraping_job()

    # Jadwalkan scraping harian
    schedule.every().day.at(_SCHEDULE_TIME_UTC).do(run_scraping_job)
    logger.info(
        "Jadwal aktif: scraping berikutnya pukul %s", _SCHEDULE_TIME_LABEL
    )

    # Loop selamanya
    while True:
        schedule.run_pending()
        time.sleep(60)  # Cek jadwal setiap menit


if __name__ == "__main__":
    main()
