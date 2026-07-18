"""
Repository untuk data toko online.

Semua query SQL yang berhubungan dengan tabel `toko_online`
harus berada di sini.
"""

from app.db.session import get_db_connection
from app.core.exceptions import DatabaseException
from app.core.logger import get_logger

logger = get_logger(__name__)


class StoreRepository:
    """Mengelola akses data ke tabel toko_online."""

    def get_all_stores(self) -> list[dict]:
        """
        Ambil semua data toko online.

        Returns:
            List dictionary berisi data toko online.

        Raises:
            DatabaseException: Jika query gagal dieksekusi.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT
                    id,
                    nama_toko,
                    platform,
                    nama_produk,
                    jenis_cabai,
                    harga,
                    satuan,
                    lokasi,
                    rating,
                    link_toko,
                    gambar_toko AS gambar_produk
                FROM toko_online
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result

        except DatabaseException:
            raise
        except Exception as exc:
            logger.error("Gagal mengambil data toko online: %s", exc)
            raise DatabaseException(
                message="Gagal mengambil data toko online.",
                detail=str(exc),
            ) from exc
