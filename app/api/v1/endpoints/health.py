"""Endpoint kesehatan aplikasi (health check)."""

from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/", summary="Health check")
def health_check() -> dict:
    """
    Kembalikan status aplikasi beserta versi.

    Returns:
        Dict berisi status dan versi aplikasi.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "message": f"{settings.app_title} aktif",
        "version": settings.app_version,
    }
