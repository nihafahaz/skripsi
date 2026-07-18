"""
Konfigurasi logging terpusat.

Semua modul di seluruh aplikasi harus menggunakan logger dari modul ini.
Tidak boleh ada print() atau logging.getLogger() langsung di luar modul ini.
"""

import logging
import sys
from app.core.config import get_settings


def setup_logging() -> None:
    """
    Inisialisasi konfigurasi logging global.

    Dipanggil sekali saat startup aplikasi.
    Format log: [timestamp] [level] [module] message
    """
    settings = get_settings()

    log_level = logging.DEBUG if settings.debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Hindari duplikasi handler jika setup dipanggil lebih dari sekali
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    # Kurangi verbosity library eksternal
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("mlflow").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Kembalikan logger dengan nama yang diberikan.

    Args:
        name: Nama logger, umumnya diisi __name__ dari modul pemanggil.

    Returns:
        logging.Logger instance.

    Example:
        >>> from app.core.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Service started.")
    """
    return logging.getLogger(name)
