"""
Scheduler otomatis untuk Training Model LSTM Global.

Menjalankan pipeline training ulang setiap Minggu pukul 02:00 WIB
agar model tetap update dengan data terbaru yang sudah di-scraping.

Cara kerja:
- Saat pertama kali dijalankan → langsung training sekali
- Selanjutnya → training dijadwalkan setiap Minggu pukul 02:00 WIB

Kenapa Minggu 02:00 WIB?
- Scraper jalan setiap hari 06:00 WIB → data selalu fresh sebelum training
- Dini hari → traffic rendah, tidak mengganggu prediksi aktif
"""

import sys
import os
import time
import datetime

import schedule

# Pastikan root project ada di sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logger import get_logger, setup_logging
from app.ml.training.trainer import run_training

logger = get_logger(__name__)

# ── Konfigurasi Jadwal ────────────────────────────────────────────────────────
# Setiap Minggu pukul 02:00 WIB (UTC+7) = Sabtu 19:00 UTC
_SCHEDULE_DAY_UTC  = "saturday"   # Saturday UTC = Minggu dini hari WIB
_SCHEDULE_TIME_UTC = "19:00"      # 19:00 UTC = 02:00 WIB
_SCHEDULE_LABEL    = "Minggu 02:00 WIB"
# ─────────────────────────────────────────────────────────────────────────────


def run_training_job() -> None:
    """
    Satu siklus pipeline training model LSTM Global.

    Dipanggil oleh scheduler maupun saat startup awal.
    """
    now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=7)

    logger.info("=" * 60)
    logger.info(
        "Memulai training terjadwal — %s WIB",
        now_wib.strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info("=" * 60)

    try:
        run_training()
        now_done = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        logger.info(
            "Training selesai pada %s WIB",
            now_done.strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as exc:
        logger.error("Training gagal: %s", exc, exc_info=True)
        logger.warning("Model lama tetap digunakan hingga training berikutnya.")


def main() -> None:
    """
    Entry point scheduler training.

    1. Setup logging
    2. Jalankan training sekali saat startup (opsional, bisa dinonaktifkan)
    3. Jadwalkan training mingguan setiap Minggu 02:00 WIB
    4. Loop selamanya
    """
    setup_logging()
    logger.info("Training Scheduler dimulai.")
    logger.info("Jadwal: setiap %s", _SCHEDULE_LABEL)

    # ── Opsional: training langsung saat startup ──────────────────────────────
    # Set TRAIN_ON_STARTUP=true di environment untuk aktifkan
    if os.getenv("TRAIN_ON_STARTUP", "false").lower() == "true":
        logger.info("TRAIN_ON_STARTUP=true → Menjalankan training awal...")
        run_training_job()
    else:
        logger.info("TRAIN_ON_STARTUP=false → Melewati training saat startup.")
    # ─────────────────────────────────────────────────────────────────────────

    # Jadwalkan training mingguan
    getattr(schedule.every(), _SCHEDULE_DAY_UTC).at(_SCHEDULE_TIME_UTC).do(
        run_training_job
    )

    # Hitung waktu training berikutnya
    next_run = schedule.next_run()
    if next_run:
        next_wib = next_run + datetime.timedelta(hours=7)
        logger.info(
            "Training berikutnya: %s WIB",
            next_wib.strftime("%A, %Y-%m-%d %H:%M:%S"),
        )

    # Loop selamanya — cek jadwal setiap menit
    logger.info("Scheduler aktif. Menunggu jadwal berikutnya...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
