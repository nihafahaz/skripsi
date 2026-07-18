"""Service untuk data toko online."""

from app.core.logger import get_logger
from app.db.repositories.store_repository import StoreRepository

logger = get_logger(__name__)
_store_repo = StoreRepository()


def get_all_stores() -> list[dict]:
    """
    Ambil semua data toko online.

    Returns:
        List dict berisi data toko online.
    """
    return _store_repo.get_all_stores()
