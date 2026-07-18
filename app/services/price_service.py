"""Service untuk data harga cabai historis."""

from app.core.logger import get_logger
from app.db.repositories.price_repository import PriceRepository

logger = get_logger(__name__)
_price_repo = PriceRepository()


def get_price_history(
    provinsi: str | None,
    jenis_cabai: str | None,
    limit: int,
) -> dict:
    """
    Ambil data harga historis dengan filter opsional.

    Args:
        provinsi: Filter provinsi (opsional).
        jenis_cabai: Filter jenis cabai (opsional).
        limit: Jumlah maksimum baris (maks 100).

    Returns:
        Dict dengan kunci 'jumlah_data' dan 'data'.
    """
    data = _price_repo.get_prices(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        limit=limit,
    )
    return {"jumlah_data": len(data), "data": data}
