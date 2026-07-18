"""
Cleaner — validasi dan pembersihan record mentah hasil scraping.

Bertanggung jawab membersihkan nilai harga dari format teks
dan memvalidasi bahwa record memiliki semua field yang diperlukan.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


def clean_price_string(raw: str) -> int | None:
    """
    Bersihkan string harga dari karakter non-numerik.

    Args:
        raw: String harga mentah (contoh: "Rp 45.000", "45000", "45.000").

    Returns:
        int harga dalam rupiah, atau None jika tidak dapat diparse.
    """
    cleaned = (
        raw.replace("Rp", "")
           .replace(".", "")
           .replace(",", "")
           .strip()
    )
    if cleaned.isdigit():
        return int(cleaned)
    return None


def clean_record(
    tanggal: str | None,
    provinsi: str | None,
    jenis_cabai: str | None,
    harga_raw: str,
) -> dict | None:
    """
    Validasi dan bersihkan satu record mentah dari parser.

    Record akan diabaikan (return None) jika salah satu field kritis
    tidak tersedia atau harga tidak valid.

    Args:
        tanggal: Tanggal dalam format YYYY-MM-DD.
        provinsi: Nama provinsi (sudah ternormalisasi ke nama resmi).
        jenis_cabai: Nama jenis cabai.
        harga_raw: String harga mentah dari website.

    Returns:
        Dict dengan kunci 'tanggal', 'provinsi', 'jenis_cabai', 'harga',
        atau None jika record tidak valid.
    """
    if not tanggal or not provinsi or not jenis_cabai:
        return None

    harga = clean_price_string(harga_raw)
    if harga is None or harga <= 0:
        logger.debug(
            "Record diabaikan — harga tidak valid: %s [%s/%s/%s]",
            harga_raw, tanggal, provinsi, jenis_cabai,
        )
        return None

    return {
        "tanggal": tanggal,
        "provinsi": provinsi,
        "jenis_cabai": jenis_cabai,
        "harga": harga,
    }
