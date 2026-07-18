"""
Model loader untuk inferensi LSTM — Singleton Pattern.

Model LSTM dan scaler dimuat SEKALI saat startup aplikasi,
lalu digunakan ulang untuk setiap request prediksi.
Ini menghindari overhead cold-start yang berat per request.
"""

import os
import joblib
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

from app.core.config import get_settings
from app.core.exceptions import MLModelException
from app.core.logger import get_logger
from app.utils.constants import LAG, NUM_FEATURES

logger = get_logger(__name__)


def build_lstm_architecture() -> Sequential:
    """
    Bangun arsitektur model LSTM global.

    Arsitektur harus sama persis dengan yang digunakan saat training
    agar bobot dapat dimuat dengan benar.

    Returns:
        Sequential: Model Keras yang belum memuat bobot.
    """
    model = Sequential([
        Input(shape=(LAG, NUM_FEATURES)),
        LSTM(get_settings().lstm_units, return_sequences=False),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(loss="mse", optimizer="adam")
    return model


class ModelLoader:
    """
    Singleton loader untuk model LSTM dan scaler.

    Gunakan `get_model_loader()` untuk mendapatkan instance tunggal.
    Jangan buat instance baru secara langsung.
    """

    def __init__(self) -> None:
        self._model: Sequential | None = None
        self._scaler = None
        self._is_loaded: bool = False

    def load(self) -> None:
        """
        Muat model weights dan scaler dari disk.

        Harus dipanggil sekali saat startup aplikasi.

        Raises:
            MLModelException: Jika file model atau scaler tidak ditemukan,
                              atau gagal saat pemuatan.
        """
        if self._is_loaded:
            logger.debug("Model sudah dimuat sebelumnya, skip reload.")
            return

        settings = get_settings()
        weights_path = settings.model_weights_path
        scaler_path = settings.scaler_path

        if not os.path.exists(weights_path):
            raise MLModelException(
                message="File weights model tidak ditemukan.",
                detail=f"Path: {weights_path}",
            )

        if not os.path.exists(scaler_path):
            raise MLModelException(
                message="File scaler tidak ditemukan.",
                detail=f"Path: {scaler_path}",
            )

        try:
            logger.info("Memuat model LSTM dari: %s", weights_path)
            self._model = build_lstm_architecture()
            self._model.load_weights(weights_path)

            logger.info("Memuat scaler dari: %s", scaler_path)
            self._scaler = joblib.load(scaler_path)

            self._is_loaded = True
            logger.info("Model dan scaler berhasil dimuat.")

        except MLModelException:
            raise
        except Exception as exc:
            logger.error("Gagal memuat model: %s", exc)
            raise MLModelException(
                message="Gagal memuat model LSTM atau scaler.",
                detail=str(exc),
            ) from exc

    @property
    def model(self) -> Sequential:
        """
        Kembalikan model LSTM yang sudah dimuat.

        Raises:
            MLModelException: Jika model belum dimuat.
        """
        if not self._is_loaded or self._model is None:
            raise MLModelException(
                message="Model belum diinisialisasi.",
                detail="Pastikan ModelLoader.load() dipanggil saat startup.",
            )
        return self._model

    @property
    def scaler(self):
        """
        Kembalikan scaler yang sudah dimuat.

        Raises:
            MLModelException: Jika scaler belum dimuat.
        """
        if not self._is_loaded or self._scaler is None:
            raise MLModelException(
                message="Scaler belum diinisialisasi.",
                detail="Pastikan ModelLoader.load() dipanggil saat startup.",
            )
        return self._scaler


# Singleton instance — satu-satunya instance yang digunakan seluruh aplikasi
_model_loader_instance: ModelLoader | None = None


def get_model_loader() -> ModelLoader:
    """
    Kembalikan singleton ModelLoader.

    Returns:
        ModelLoader: Instance yang sudah (atau belum) memuat model.
    """
    global _model_loader_instance
    if _model_loader_instance is None:
        _model_loader_instance = ModelLoader()
    return _model_loader_instance
