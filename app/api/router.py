"""
Router utama API v1.

Menggabungkan semua endpoint dari modul-modul terpisah
menjadi satu router yang di-mount ke aplikasi FastAPI.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, prices, predictions, reports, stores

router = APIRouter()

# Mount semua endpoint
router.include_router(health.router)
router.include_router(prices.router)
router.include_router(predictions.router)
router.include_router(stores.router)
router.include_router(reports.router)
