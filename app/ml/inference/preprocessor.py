"""
Preprocessing untuk inferensi (prediksi runtime).

Modul ini bertanggung jawab mempersiapkan data historis menjadi
tensor input yang siap diumpankan ke model LSTM, termasuk:
- LOCF (Last Observation Carried Forward) untuk hari libur/akhir pekan
- Scaling dengan MinMaxScaler global
- One-Hot Encoding provinsi dan jenis cabai
- Pembentukan feature matrix 3D [1, LAG, NUM_FEATURES]
"""

from datetime import date, timedelta

import numpy as np

from app.core.exceptions import InsufficientDataException
from app.core.logger import get_logger
from app.utils.constants import (
    JENIS_CABAI_LIST,
    LAG,
    NUM_FEATURES,
    PROVINSI_LIST,
)

logger = get_logger(__name__)


def apply_locf(
    data_historis: list[dict],
    lag: int = LAG,
) -> list[dict]:
    """
    Terapkan LOCF (Last Observation Carried Forward) untuk mengisi gap
    akhir pekan atau hari libur.

    Jika data terakhir di database lebih tua dari hari ini (selisih 1–7 hari),
    salin harga hari kerja terakhir ke hari-hari berikutnya hingga hari ini.

    Args:
        data_historis: List dict berisi 'tanggal' (date) dan 'harga' (float),
                       urut dari terlama ke terbaru.
        lag: Ukuran window yang dibutuhkan model.

    Returns:
        List dict setelah LOCF diterapkan (panjang tetap lag).
    """
    hari_ini: date = date.today()
    tanggal_terakhir_db: date = data_historis[-1]["tanggal"]
    delta_hari: int = (hari_ini - tanggal_terakhir_db).days

    if 0 < delta_hari <= 7:
        logger.debug(
            "LOCF: mengisi gap %d hari dari %s ke %s",
            delta_hari, tanggal_terakhir_db, hari_ini,
        )
        tanggal_iter = tanggal_terakhir_db
        while tanggal_iter < hari_ini:
            tanggal_iter += timedelta(days=1)
            new_record = {
                "tanggal": tanggal_iter,
                "harga": data_historis[-1]["harga"],
            }
            data_historis.append(new_record)
            if len(data_historis) > lag:
                data_historis.pop(0)

    return data_historis


def build_input_tensor(
    data_historis: list[dict],
    provinsi: str,
    jenis_cabai: str,
    scaler,
) -> tuple[np.ndarray, np.ndarray, date, float]:
    """
    Bangun tensor input 3D untuk model LSTM dari data historis.

    Args:
        data_historis: List dict {'tanggal': date, 'harga': float},
                       urut terlama ke terbaru, panjang == LAG.
        provinsi: Nama provinsi untuk OHE.
        jenis_cabai: Jenis cabai untuk OHE.
        scaler: MinMaxScaler yang sudah di-fit (global scaler).

    Returns:
        Tuple (input_tensor, ohe_features, tanggal_terakhir, harga_terakhir).
        - input_tensor: np.ndarray shape (1, LAG, NUM_FEATURES).
        - ohe_features: np.ndarray shape (NUM_FEATURES - 1,) untuk sliding window.
        - tanggal_terakhir: Tanggal data historis terakhir.
        - harga_terakhir: Harga data historis terakhir (sebelum scaling).

    Raises:
        InsufficientDataException: Jika panjang data_historis < LAG.
    """
    if len(data_historis) < LAG:
        raise InsufficientDataException(
            message=f"Data historis tidak cukup. Butuh minimal {LAG} hari.",
            detail=(
                f"Tersedia: {len(data_historis)} baris "
                f"untuk {provinsi} / {jenis_cabai}."
            ),
        )

    tanggal_terakhir: date = data_historis[-1]["tanggal"]
    harga_terakhir: float = float(data_historis[-1]["harga"])

    # --- Scaling harga ---
    harga_sequence = np.array(
        [float(item["harga"]) for item in data_historis]
    ).reshape(-1, 1)
    scaled_sequence: np.ndarray = scaler.transform(harga_sequence)

    # --- One-Hot Encoding ---
    prov_idx = PROVINSI_LIST.index(provinsi)
    chili_idx = JENIS_CABAI_LIST.index(jenis_cabai)

    prov_ohe = np.zeros(len(PROVINSI_LIST))
    prov_ohe[prov_idx] = 1.0

    chili_ohe = np.zeros(len(JENIS_CABAI_LIST))
    chili_ohe[chili_idx] = 1.0

    ohe_features: np.ndarray = np.concatenate([prov_ohe, chili_ohe])  # (38,)

    # --- Bangun tensor [1, LAG, NUM_FEATURES] ---
    input_tensor = np.zeros((1, LAG, NUM_FEATURES))
    for t in range(LAG):
        input_tensor[0, t, 0] = scaled_sequence[t, 0]
        input_tensor[0, t, 1:] = ohe_features

    return input_tensor, ohe_features, tanggal_terakhir, harga_terakhir


def slide_window(
    current_tensor: np.ndarray,
    pred_scaled: np.ndarray,
    ohe_features: np.ndarray,
) -> np.ndarray:
    """
    Geser window satu langkah ke depan untuk prediksi multi-step.

    Args:
        current_tensor: Tensor input saat ini, shape (1, LAG, NUM_FEATURES).
        pred_scaled: Nilai prediksi hari ini (scaled), shape (1, 1).
        ohe_features: OHE features yang tetap sama, shape (NUM_FEATURES - 1,).

    Returns:
        np.ndarray: Tensor baru setelah geser, shape (1, LAG, NUM_FEATURES).
    """
    lag = current_tensor.shape[1]
    next_tensor = np.zeros_like(current_tensor)

    # Geser harga historis ke kiri (drop hari terlama)
    next_tensor[0, :lag - 1, 0] = current_tensor[0, 1:, 0]
    # Isi slot terakhir dengan hasil prediksi hari ini
    next_tensor[0, -1, 0] = pred_scaled[0][0]
    # OHE tetap sama di semua timestep
    for t in range(lag):
        next_tensor[0, t, 1:] = ohe_features

    return next_tensor
