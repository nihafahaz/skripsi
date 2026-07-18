"""
Trainer pipeline model LSTM Global.

Mengorkestrasikan seluruh proses training:
1. Ambil data dari database
2. Split train/test secara temporal
3. Interpolasi missing value
4. Fit global scaler (hanya pada data train)
5. Bangun feature tensor dengan OHE
6. Training model LSTM dengan MLflow tracking
7. Simpan weights dan scaler ke disk
"""

import os

import joblib
import mlflow
import mlflow.tensorflow
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.layers import LSTM
from tensorflow.keras.models import Sequential

from app.core.config import get_settings
from app.core.logger import get_logger
from app.db.session import get_db_connection
from app.ml.training.data_builder import build_feature_tensor
from app.ml.training.preprocessing import clean_price, interpolate_missing
from app.utils.constants import (
    JENIS_CABAI_LIST,
    LAG,
    NUM_FEATURES,
    PROVINSI_LIST,
)

import pandas as pd

logger = get_logger(__name__)


def _fetch_series_data(cursor) -> list[tuple]:
    """
    Ambil data mentah dari database untuk semua kombinasi provinsi/jenis.

    Returns:
        List of (train_df, test_df, prov_idx, chili_idx).
    """
    settings = get_settings()
    split_ratio = settings.split_ratio
    series_data_list: list[tuple] = []
    all_train_prices: list[float] = []

    logger.info("Tahap 1: Mengambil dan membagi data dari database...")

    for prov_idx, provinsi in enumerate(PROVINSI_LIST):
        for chili_idx, jenis in enumerate(JENIS_CABAI_LIST):
            cursor.execute(
                """
                SELECT tanggal, harga
                FROM data_harga_clean
                WHERE provinsi = %s AND jenis_cabai = %s
                ORDER BY tanggal ASC
                """,
                (provinsi, jenis),
            )
            rows = cursor.fetchall()

            if len(rows) < (LAG + 10):
                continue

            data = pd.DataFrame(rows)
            data["tanggal"] = pd.to_datetime(data["tanggal"])
            data = data.sort_values("tanggal").reset_index(drop=True)
            data["harga"] = data["harga"].apply(clean_price)

            n_train = int(len(data) * split_ratio)
            train_df = data.iloc[:n_train].copy().reset_index(drop=True)
            test_df = data.iloc[n_train:].copy().reset_index(drop=True)

            # --- SIMPAN SPLIT DATA MENTAH SEBELUM PREPROCESSING ---
            split_dir = "split"
            os.makedirs(split_dir, exist_ok=True)
            
            # Format nama file: split/DKI_Jakarta_Cabai_Rawit_Merah_train.xlsx
            sanitized_prov = provinsi.replace(" ", "_")
            sanitized_jenis = jenis.replace(" ", "_")
            train_split_path = os.path.join(split_dir, f"{sanitized_prov}_{sanitized_jenis}_train.xlsx")
            test_split_path = os.path.join(split_dir, f"{sanitized_prov}_{sanitized_jenis}_test.xlsx")

            # Ubah datetime ke string date untuk kemudahan Excel
            train_excel = train_df.copy()
            train_excel["tanggal"] = train_excel["tanggal"].dt.date
            test_excel = test_df.copy()
            test_excel["tanggal"] = test_excel["tanggal"].dt.date

            train_excel.to_excel(train_split_path, index=False)
            test_excel.to_excel(test_split_path, index=False)

            # --- LANJUTKAN PREPROCESSING (INTERPOLASI & PEMBULATAN) ---
            label = f"{provinsi} / {jenis}"
            train_df = interpolate_missing(train_df, label=f"{label} [train]")
            test_df = interpolate_missing(test_df, label=f"{label} [test]")

            # Bulatkan ke 100 terdekat setelah interpolasi
            train_df["harga"] = (train_df["harga"] / 100).round() * 100
            test_df["harga"] = (test_df["harga"] / 100).round() * 100

            all_train_prices.extend(train_df["harga"].values)
            series_data_list.append((train_df, test_df, prov_idx, chili_idx))

    return series_data_list, all_train_prices


def run_training() -> None:
    """
    Jalankan pipeline training LSTM Global dengan MLflow tracking.

    Menyimpan weights ke `settings.model_weights_path`
    dan scaler ke `settings.scaler_path`.
    """
    settings = get_settings()

    logger.info("Memulai training model LSTM Global...")

    # --- Setup MLflow ---
    logger.info("Menghubungkan ke MLflow: %s", settings.mlflow_tracking_uri)
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    try:
        mlflow.create_experiment(settings.mlflow_experiment_name)
    except Exception:
        pass
    mlflow.set_experiment(settings.mlflow_experiment_name)
    mlflow.tensorflow.autolog()

    os.makedirs(os.path.dirname(settings.model_weights_path), exist_ok=True)
    os.makedirs(os.path.dirname(settings.scaler_path), exist_ok=True)

    # --- Ambil data ---
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    series_data_list, all_train_prices = _fetch_series_data(cursor)

    cursor.close()
    connection.close()

    if not series_data_list:
        logger.error("Tidak ada data yang cukup untuk training!")
        return

    # --- Fit global scaler (hanya dari data train) ---
    logger.info("Tahap 2: Fitting MinMaxScaler Global dari data Train...")
    all_train_arr = np.array(all_train_prices, dtype=float).reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(all_train_arr)
    joblib.dump(scaler, settings.scaler_path)
    logger.info("Scaler disimpan ke: %s", settings.scaler_path)

    # --- Bangun feature tensor ---
    logger.info("Tahap 3: Membangun feature tensor (scaling + supervised lags)...")
    train_x_list, train_y_list = [], []
    test_x_list, test_y_list = [], []

    for train_df, test_df, prov_idx, chili_idx in series_data_list:
        train_prices = train_df["harga"].values.reshape(-1, 1).astype(float)
        test_prices = test_df["harga"].values.reshape(-1, 1).astype(float)

        scaled_train = scaler.transform(train_prices)
        scaled_test = scaler.transform(test_prices)

        prov_ohe = np.zeros(len(PROVINSI_LIST))
        prov_ohe[prov_idx] = 1.0

        chili_ohe = np.zeros(len(JENIS_CABAI_LIST))
        chili_ohe[chili_idx] = 1.0

        train_x, train_y = build_feature_tensor(scaled_train, prov_ohe, chili_ohe, LAG)

        # Test: gabungkan LAG terakhir dari train agar tidak memotong awal test
        test_input_seq = np.concatenate([scaled_train[-LAG:], scaled_test], axis=0)
        test_x, test_y = build_feature_tensor(test_input_seq, prov_ohe, chili_ohe, LAG)

        train_x_list.append(train_x)
        train_y_list.append(train_y)
        test_x_list.append(test_x)
        test_y_list.append(test_y)

    final_train_x = np.concatenate(train_x_list, axis=0)
    final_train_y = np.concatenate(train_y_list, axis=0)
    final_test_x = np.concatenate(test_x_list, axis=0)
    final_test_y = np.concatenate(test_y_list, axis=0)

    logger.info("Shape train: %s | Shape test: %s", final_train_x.shape, final_test_x.shape)

    # --- Training ---
    with mlflow.start_run(run_name="Run_Model_LSTM_Global") as run:
        logger.info("Memulai fitting model LSTM Global...")

        model = Sequential([
            Input(shape=(final_train_x.shape[1], final_train_x.shape[2])),
            LSTM(settings.lstm_units, return_sequences=False),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(loss="mse", optimizer="adam")

        early_stopping = EarlyStopping(
            monitor="val_loss",
            patience=25,
            restore_best_weights=True,
        )

        history = model.fit(
            final_train_x, final_train_y,
            epochs=settings.epochs,
            batch_size=settings.batch_size,
            validation_data=(final_test_x, final_test_y),
            callbacks=[early_stopping],
            verbose=1,
            shuffle=False,
        )

        # --- Evaluasi ---
        yhat = np.clip(model.predict(final_test_x), 0, 1)
        inv_yhat = scaler.inverse_transform(yhat)[:, 0]
        inv_y = scaler.inverse_transform(
            final_test_y.reshape(-1, 1)
        )[:, 0]

        mape = float(np.mean(np.abs((inv_y - inv_yhat) / inv_y)) * 100)
        rmse = float(np.sqrt(mean_squared_error(inv_y, inv_yhat)))
        mae = float(mean_absolute_error(inv_y, inv_yhat))
        final_loss = float(history.history["loss"][-1])

        # --- Log ke MLflow ---
        mlflow.log_param("lstm_units", settings.lstm_units)
        mlflow.log_param("lag", LAG)
        mlflow.log_param("split_ratio", settings.split_ratio)
        mlflow.log_param("epochs", settings.epochs)
        mlflow.log_param("batch_size", settings.batch_size)
        mlflow.log_param("total_features", final_train_x.shape[2])

        mlflow.log_metric("final_train_loss_mse", final_loss)
        mlflow.log_metric("global_mape", mape)
        mlflow.log_metric("global_rmse", rmse)
        mlflow.log_metric("global_mae", mae)

        # --- Simpan weights ---
        model.save_weights(settings.model_weights_path)
        logger.info("Weights disimpan ke: %s", settings.model_weights_path)

        logger.info(
            "Training selesai! RMSE=%.2f | MAE=%.2f | MAPE=%.2f%% | Run ID=%s",
            rmse, mae, mape, run.info.run_id,
        )
