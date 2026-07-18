"""
Mapper — normalisasi nama provinsi dari sumber data eksternal.

Menangani perbedaan penulisan nama provinsi antara website BI PIHPS
dengan standar nama yang digunakan dalam database.
"""

import re

from app.utils.constants import PROVINSI_LIST


def normalize_province_name(raw_name: str) -> str:
    """
    Normalisasi nama provinsi: uppercase, hapus semua non-alfanumerik.

    Args:
        raw_name: Nama provinsi mentah dari sumber scraping.

    Returns:
        str: Nama ternormalisasi (hanya huruf dan angka, uppercase).
    """
    return re.sub(r"[^A-Z0-9]", "", raw_name.upper().strip())


# Mapping dari nama ternormalisasi ke nama resmi dalam database
NORMALIZED_PROVINCE_MAP: dict[str, str] = {
    normalize_province_name(p): p for p in PROVINSI_LIST
}


def get_canonical_province_name(raw_name: str) -> str | None:
    """
    Kembalikan nama provinsi resmi berdasarkan nama mentah.

    Args:
        raw_name: Nama provinsi mentah dari sumber scraping.

    Returns:
        str jika ditemukan di peta, None jika tidak dikenali.
    """
    normalized = normalize_province_name(raw_name)
    return NORMALIZED_PROVINCE_MAP.get(normalized)
