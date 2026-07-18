"""
Repository scraper — persistance data hasil scraping ke database.
"""

from app.core.exceptions import DatabaseException
from app.core.logger import get_logger
from app.db.session import get_db_connection

logger = get_logger(__name__)


def save_records(records: list[dict]) -> dict[str, int]:
    """
    Simpan atau perbarui record harga ke database MySQL.

    Menggunakan strategi UPSERT:
    - Jika record dengan (tanggal, provinsi, jenis_cabai) sudah ada
      dan harganya berbeda → UPDATE.
    - Jika belum ada → INSERT.

    Args:
        records: List dict dengan kunci 'tanggal', 'provinsi',
                 'jenis_cabai', 'harga'.

    Returns:
        Dict {'inserted': int, 'updated': int}.

    Raises:
        DatabaseException: Jika koneksi atau query gagal.
    """
    inserted = 0
    updated = 0

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        for rec in records:
            cursor.execute(
                """
                SELECT id, harga FROM data_harga_clean
                WHERE tanggal = %s AND provinsi = %s AND jenis_cabai = %s
                """,
                (rec["tanggal"], rec["provinsi"], rec["jenis_cabai"]),
            )
            existing = cursor.fetchone()

            if existing:
                db_id, db_harga = existing
                if db_harga != rec["harga"]:
                    cursor.execute(
                        "UPDATE data_harga_clean SET harga = %s WHERE id = %s",
                        (rec["harga"], db_id),
                    )
                    updated += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO data_harga_clean
                        (tanggal, provinsi, jenis_cabai, harga)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (rec["tanggal"], rec["provinsi"], rec["jenis_cabai"], rec["harga"]),
                )
                inserted += 1

        connection.commit()
        cursor.close()
        connection.close()

        logger.info(
            "Sinkronisasi selesai: %d inserted, %d updated.", inserted, updated
        )
        return {"inserted": inserted, "updated": updated}

    except DatabaseException:
        raise
    except Exception as exc:
        logger.error("Gagal menyimpan data scraper ke database: %s", exc)
        raise DatabaseException(
            message="Gagal menyimpan data scraper ke database.",
            detail=str(exc),
        ) from exc
