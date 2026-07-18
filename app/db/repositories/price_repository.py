"""
Repository untuk data harga cabai historis.

Semua query SQL yang berhubungan dengan tabel `data_harga_clean`
harus berada di sini. Layer service tidak boleh menulis SQL secara langsung.
"""

from app.db.session import get_db_connection
from app.core.exceptions import DatabaseException
from app.core.logger import get_logger

logger = get_logger(__name__)


class PriceRepository:
    """Mengelola akses data ke tabel data_harga_clean."""

    def get_prices(
        self,
        provinsi: str | None = None,
        jenis_cabai: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Ambil data harga cabai historis dengan filter opsional.

        Args:
            provinsi: Filter berdasarkan nama provinsi.
            jenis_cabai: Filter berdasarkan jenis cabai.
            limit: Jumlah maksimum baris yang dikembalikan (maks 100).

        Returns:
            List dictionary berisi data harga, diurutkan terbaru.

        Raises:
            DatabaseException: Jika query gagal dieksekusi.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = "SELECT * FROM data_harga_clean WHERE 1=1"
            params: list = []

            if provinsi:
                query += " AND provinsi = %s"
                params.append(provinsi)

            if jenis_cabai:
                query += " AND jenis_cabai = %s"
                params.append(jenis_cabai)

            query += " ORDER BY tanggal DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result

        except DatabaseException:
            raise
        except Exception as exc:
            logger.error("Gagal mengambil data harga: %s", exc)
            raise DatabaseException(
                message="Gagal mengambil data harga.",
                detail=str(exc),
            ) from exc

    def get_recent_prices_for_prediction(
        self,
        provinsi: str,
        jenis_cabai: str,
        lag: int,
    ) -> list[dict]:
        """
        Ambil data harga terbaru untuk digunakan sebagai input prediksi.

        Mengambil `lag` baris terbaru untuk kombinasi provinsi dan jenis cabai
        yang diberikan, diurutkan dari terlama ke terbaru.

        Args:
            provinsi: Nama provinsi.
            jenis_cabai: Jenis cabai.
            lag: Jumlah hari historis yang dibutuhkan model.

        Returns:
            List dict berisi kunci 'tanggal' dan 'harga', urut terlama.

        Raises:
            DatabaseException: Jika query gagal dieksekusi.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT tanggal, harga
                FROM data_harga_clean
                WHERE provinsi = %s
                  AND jenis_cabai = %s
                ORDER BY tanggal DESC
                LIMIT %s
            """
            cursor.execute(query, (provinsi, jenis_cabai, lag))
            rows = cursor.fetchall()

            cursor.close()
            connection.close()

            # Balik urutan: dari terlama ke terbaru
            return list(reversed(rows))

        except DatabaseException:
            raise
        except Exception as exc:
            logger.error(
                "Gagal mengambil data historis untuk prediksi [%s/%s]: %s",
                provinsi, jenis_cabai, exc,
            )
            raise DatabaseException(
                message="Gagal mengambil data historis untuk prediksi.",
                detail=str(exc),
            ) from exc

    def get_distinct_combinations(self) -> list[tuple[str, str]]:
        """
        Ambil semua kombinasi unik (provinsi, jenis_cabai) dari database.

        Returns:
            List tuple (provinsi, jenis_cabai).

        Raises:
            DatabaseException: Jika query gagal dieksekusi.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                "SELECT DISTINCT provinsi, jenis_cabai FROM data_harga_clean"
            )
            rows = cursor.fetchall()

            cursor.close()
            connection.close()

            return [(row[0], row[1]) for row in rows]

        except DatabaseException:
            raise
        except Exception as exc:
            logger.error("Gagal mengambil kombinasi data: %s", exc)
            raise DatabaseException(
                message="Gagal mengambil kombinasi data.",
                detail=str(exc),
            ) from exc
