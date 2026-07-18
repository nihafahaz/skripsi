"""Endpoint data harga cabai historis."""

from fastapi import APIRouter, Query
from app.services.price_service import get_price_history

router = APIRouter(prefix="/harga", tags=["Harga Historis"])


@router.get("", summary="Ambil data harga historis")
def get_prices(
    provinsi: str | None = Query(default=None, description="Filter berdasarkan provinsi."),
    jenis_cabai: str | None = Query(default=None, description="Filter berdasarkan jenis cabai."),
    limit: int = Query(default=10, ge=1, le=100, description="Jumlah maksimum data."),
) -> dict:
    """
    Ambil data harga cabai historis dari database.

    Filter provinsi dan jenis_cabai bersifat opsional.
    Data diurutkan dari tanggal terbaru.
    """
    return get_price_history(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        limit=limit,
    )
