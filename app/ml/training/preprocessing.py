"""
Fungsi preprocessing untuk pipeline training model LSTM.

Berisi utilitas pembersihan harga dan interpolasi missing value
yang digunakan saat mempersiapkan data training.
"""

import numpy as np
import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)


def clean_price(nilai) -> float | None:
    """
    Bersihkan nilai harga dari karakter non-numerik.

    Args:
        nilai: Nilai harga dalam berbagai format (str, int, float, NaN).

    Returns:
        float jika valid, None jika tidak dapat diparse.
    """
    if pd.isna(nilai):
        return None

    if isinstance(nilai, (int, float, np.integer, np.floating)):
        return float(nilai)

    nilai = str(nilai).strip()

    if nilai in ("", "-", "nan", "None"):
        return None

    nilai = nilai.replace(",", "").replace(".", "")
    return pd.to_numeric(nilai, errors="coerce")


def interpolate_missing(
    data: pd.DataFrame,
    label: str = "kombinasi",
) -> pd.DataFrame:
    """
    Isi missing value kolom 'harga' menggunakan metode gabungan:
    - Bagian dalam (interior): Spline order 3 (fallback ke linear)
    - Bagian luar (eksterior): bfill + ffill

    Teknik ini mencegah ekstrapolasi berlebihan di ujung-ujung data.

    Args:
        data: DataFrame dengan kolom 'harga'. Index harus berurutan.
        label: Label untuk pesan log (misal "Jawa Barat / Cabai Rawit Merah").

    Returns:
        DataFrame dengan kolom 'harga' yang sudah diisi.
    """
    non_nan_indices = data[data["harga"].notna()].index

    if len(non_nan_indices) < 2:
        logger.warning(
            "[%s] Data riil terlalu sedikit (<2), gunakan linear fallback.", label
        )
        data["harga"] = data["harga"].interpolate(
            method="linear", limit_direction="both"
        )
        data["harga"] = data["harga"].bfill().ffill()
        return data

    first_idx = non_nan_indices[0]
    last_idx = non_nan_indices[-1]

    inside_series = data.loc[first_idx:last_idx, "harga"]

    if inside_series.isna().any():
        try:
            original_inside = inside_series.copy()
            interpolated = original_inside.interpolate(method="spline", order=3)

            if (
                (interpolated < 0).any()
                or (interpolated > 500_000).any()
                or interpolated.isna().any()
            ):
                raise ValueError("Spline menghasilkan nilai di luar jangkauan.")

            data.loc[first_idx:last_idx, "harga"] = interpolated

        except Exception as exc:
            logger.debug("[%s] Spline gagal (%s), fallback ke linear.", label, exc)
            data.loc[first_idx:last_idx, "harga"] = inside_series.interpolate(
                method="linear"
            )

    # Isi sisa (eksterior / ujung-ujung)
    data["harga"] = data["harga"].interpolate(
        method="linear", limit_direction="both"
    )
    data["harga"] = data["harga"].bfill().ffill()

    return data
