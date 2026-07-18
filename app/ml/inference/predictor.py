"""
Predictor — eksekusi forward-pass model LSTM dan inverse transform.

Modul ini bertanggung jawab atas:
- Menjalankan model.predict() untuk satu langkah
- Inverse transform hasil prediksi scaled ke harga asli
- Melakukan prediksi multi-step (autoregressive) selama `durasi` hari
"""

from datetime import date, timedelta

import numpy as np

from app.core.exceptions import MLModelException
from app.core.logger import get_logger
from app.ml.inference.preprocessor import slide_window

logger = get_logger(__name__)


def predict_single_step(
    model,
    scaler,
    input_tensor: np.ndarray,
) -> tuple[int, np.ndarray]:
    """
    Lakukan prediksi satu langkah ke depan.

    Args:
        model: Model LSTM yang sudah dimuat.
        scaler: MinMaxScaler global.
        input_tensor: Tensor input shape (1, LAG, NUM_FEATURES).

    Returns:
        Tuple (harga_prediksi_bulat, pred_scaled):
        - harga_prediksi_bulat: Harga dalam rupiah (int, dibulatkan).
        - pred_scaled: Nilai prediksi sebelum inverse transform, shape (1, 1).

    Raises:
        MLModelException: Jika proses prediksi gagal.
    """
    try:
        pred_scaled: np.ndarray = model.predict(input_tensor, verbose=0)
        pred_harga: float = float(scaler.inverse_transform(pred_scaled)[0][0])
        return int(round(pred_harga)), pred_scaled
    except Exception as exc:
        logger.error("Gagal menjalankan prediksi satu langkah: %s", exc)
        raise MLModelException(
            message="Gagal menjalankan inferensi model.",
            detail=str(exc),
        ) from exc


def predict_multi_step(
    model,
    scaler,
    initial_tensor: np.ndarray,
    ohe_features: np.ndarray,
    tanggal_terakhir: date,
    durasi: int,
) -> list[dict]:
    """
    Lakukan prediksi autoregressive selama `durasi` hari ke depan.

    Setiap prediksi menjadi input bagi prediksi hari berikutnya
    menggunakan teknik sliding window.

    Args:
        model: Model LSTM yang sudah dimuat.
        scaler: MinMaxScaler global.
        initial_tensor: Tensor awal, shape (1, LAG, NUM_FEATURES).
        ohe_features: OHE features (38,) yang tetap konstan.
        tanggal_terakhir: Tanggal data historis terakhir.
        durasi: Jumlah hari ke depan yang akan diprediksi.

    Returns:
        List dict berisi 'tanggal' (str YYYY-MM-DD) dan 'harga' (int).

    Raises:
        MLModelException: Jika prediksi gagal di salah satu langkah.
    """
    hasil_prediksi: list[dict] = []
    current_tensor = initial_tensor.copy()

    logger.debug("Memulai prediksi autoregressive %d hari.", durasi)

    for i in range(durasi):
        harga, pred_scaled = predict_single_step(model, scaler, current_tensor)

        tanggal_prediksi: date = tanggal_terakhir + timedelta(days=i + 1)

        hasil_prediksi.append({
            "tanggal": tanggal_prediksi.strftime("%Y-%m-%d"),
            "harga": harga,
        })

        current_tensor = slide_window(current_tensor, pred_scaled, ohe_features)

    logger.debug("Prediksi selesai: %d hari.", len(hasil_prediksi))
    return hasil_prediksi
