"""
Database session management.

Menyediakan koneksi database yang dapat diinjeksikan melalui FastAPI Depends().
Semua interaksi dengan database harus menggunakan fungsi dari modul ini —
tidak boleh ada koneksi manual di luar layer repository.
"""

import pymysql
import pymysql.cursors
from app.core.config import get_settings
from app.core.exceptions import DatabaseException
from app.core.logger import get_logger

logger = get_logger(__name__)


class _DictConnection(pymysql.connections.Connection):
    """
    Wrapper tipis di atas koneksi PyMySQL untuk mendukung
    parameter `dictionary=True` pada cursor().
    """

    def cursor(self, cursor=None, dictionary: bool = False):  # type: ignore[override]
        if dictionary:
            return super().cursor(pymysql.cursors.DictCursor)
        return super().cursor(cursor)


def get_db_connection() -> _DictConnection:
    """
    Buat dan kembalikan koneksi database baru.

    Konfigurasi koneksi dibaca dari Settings (via .env).
    Pemanggil bertanggung jawab menutup koneksi setelah selesai.

    Returns:
        _DictConnection: Koneksi PyMySQL aktif.

    Raises:
        DatabaseException: Jika koneksi gagal dibuat.
    """
    settings = get_settings()
    try:
        connection = _DictConnection(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset="utf8mb4",
        )
        return connection
    except Exception as exc:
        logger.error("Gagal membuat koneksi database: %s", exc)
        raise DatabaseException(
            message="Tidak dapat terhubung ke database.",
            detail=str(exc),
        ) from exc
