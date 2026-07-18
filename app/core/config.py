"""
Manajemen konfigurasi terpusat menggunakan Pydantic BaseSettings.

Semua nilai konfigurasi dibaca dari environment variables / file .env.
Tidak boleh ada magic value (hardcoded string/integer) di seluruh codebase.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Konfigurasi aplikasi.

    Nilai dibaca dari environment variables atau file .env di root project.
    Semua field memiliki default yang aman untuk development lokal.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "db_cabai"

    # --- MLflow ---
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "Prediksi_Harga_Cabai_LSTM_Global"

    # --- Model paths ---
    model_weights_path: str = "models/global_lstm.weights.h5"
    scaler_path: str = "scalers/global_scaler.save"

    # --- Scraper ---
    chrome_bin: str = "/usr/bin/chromium"
    chromedriver_path: str = "/usr/bin/chromedriver"
    scraper_target_url: str = (
        "https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas"
    )

    # --- Training hyperparameters ---
    lstm_units: int = 32
    epochs: int = 150
    batch_size: int = 32
    split_ratio: float = 0.8

    # --- Data synthesis ---
    synthesis_max_rows: int = 800

    # --- App ---
    app_title: str = "Backend Prediksi Harga Cabai"
    app_version: str = "2.0.0"
    debug: bool = False

    @property
    def db_url(self) -> str:
        """SQLAlchemy connection URL untuk MySQL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Kembalikan instance Settings yang di-cache (singleton).

    Menggunakan lru_cache sehingga file .env hanya dibaca sekali
    selama lifetime aplikasi.
    """
    return Settings()
