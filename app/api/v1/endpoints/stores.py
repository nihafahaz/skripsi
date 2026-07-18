"""Endpoint data toko online cabai."""

from fastapi import APIRouter
from app.services.store_service import get_all_stores

router = APIRouter(prefix="/toko_online", tags=["Toko Online"])


@router.get("", summary="Ambil data toko online cabai")
def get_stores() -> dict:
    """
    Ambil semua data toko online yang menjual produk cabai.

    Data mencakup nama toko, platform, harga, rating, dan link toko.
    """
    data = get_all_stores()
    return {"status": "success", "data": data}
