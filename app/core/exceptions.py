"""
Custom exception hierarchy untuk aplikasi prediksi harga cabai.

Setiap layer memiliki exception khusus yang akan ditangkap oleh
global exception handler di FastAPI dan diubah menjadi HTTP response
yang konsisten dan informatif.
"""

from fastapi import HTTPException, status


# =============================================================================
# Base Exception
# =============================================================================

class AppException(Exception):
    """
    Base exception untuk seluruh aplikasi.

    Semua custom exception harus mewarisi dari kelas ini
    agar mudah di-catch di level global handler.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail or message
        super().__init__(self.message)


# =============================================================================
# Database Exceptions
# =============================================================================

class DatabaseException(AppException):
    """Gagal terhubung atau menjalankan query ke database."""


class RecordNotFoundException(AppException):
    """Data yang dicari tidak ditemukan di database."""


# =============================================================================
# ML / Inference Exceptions
# =============================================================================

class MLModelException(AppException):
    """Gagal memuat, menginisialisasi, atau menjalankan model ML."""


class InsufficientDataException(AppException):
    """Data historis tidak cukup untuk melakukan prediksi."""


# =============================================================================
# Validation / Input Exceptions
# =============================================================================

class InvalidInputException(AppException):
    """Input dari pengguna tidak valid (provinsi/jenis cabai tidak dikenali)."""


# =============================================================================
# Scraper Exceptions
# =============================================================================

class ScraperException(AppException):
    """Gagal melakukan proses scraping."""


class ParserException(AppException):
    """Gagal mem-parsing data hasil scraping."""


# =============================================================================
# FastAPI Exception Handlers
# =============================================================================

def to_http_exception(exc: AppException, status_code: int) -> HTTPException:
    """Konversi AppException menjadi FastAPI HTTPException."""
    return HTTPException(
        status_code=status_code,
        detail={"message": exc.message, "detail": exc.detail},
    )


def get_http_status(exc: AppException) -> int:
    """Tentukan HTTP status code yang sesuai berdasarkan tipe exception."""
    mapping: dict[type, int] = {
        InvalidInputException: status.HTTP_400_BAD_REQUEST,
        InsufficientDataException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RecordNotFoundException: status.HTTP_404_NOT_FOUND,
        DatabaseException: status.HTTP_503_SERVICE_UNAVAILABLE,
        MLModelException: status.HTTP_503_SERVICE_UNAVAILABLE,
        ScraperException: status.HTTP_502_BAD_GATEWAY,
        ParserException: status.HTTP_502_BAD_GATEWAY,
    }
    return mapping.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
