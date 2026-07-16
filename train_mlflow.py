import os
import numpy as np
import pandas as pd
import mlflow
import mlflow.tensorflow
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
from database import get_db_connection
from preprocessing import interpolasi_missing_value, bersihkan_harga

PROVINSI_LIST = sorted([
    'Aceh', 'Bali', 'Banten', 'Bengkulu', 'DI Yogyakarta', 'DKI Jakarta',
    'Gorontalo', 'Jambi', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur',
    'Kalimantan Barat', 'Kalimantan Selatan', 'Kalimantan Tengah',
    'Kalimantan Timur', 'Kalimantan Utara', 'Kepulauan Bangka Belitung',
    'Kepulauan Riau', 'Lampung', 'Maluku', 'Maluku Utara',
    'Nusa Tenggara Barat', 'Nusa Tenggara Timur', 'Papua', 'Papua Barat',
    'Riau', 'Sulawesi Barat', 'Sulawesi Selatan', 'Sulawesi Tengah',
    'Sulawesi Tenggara', 'Sulawesi Utara', 'Sumatera Barat',
    'Sumatera Selatan', 'Sumatera Utara'
])

JENIS_CABAI_LIST = sorted([
    'Cabai Merah Besar',
    'Cabai Merah Keriting',
    'Cabai Rawit Merah',
    'Cabai Rawit Hijau'
])

NUM_PROVINSI = len(PROVINSI_LIST)  # 34
NUM_JENIS = len(JENIS_CABAI_LIST)    # 4
# Total fitur = 1 (harga) + 34 (OHE prov) + 4 (OHE jenis) = 39

EPOCHS = 150
BATCH_SIZE = 32
LSTM_UNITS = 32
SPLIT_RATIO = 0.8
# LAG = 1
LAG = 7


def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    """Mengubah data time series menjadi format supervised learning."""
    n_vars = 1 if len(data.shape) == 1 else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = list(), list()

    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j + 1, i)) for j in range(n_vars)]

    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j + 1, i)) for j in range(n_vars)]

    agg = pd.concat(cols, axis=1)
    agg.columns = names
    if dropnan:
        agg.dropna(inplace=True)
    return agg


def main():
    print("[*] Memulai training 1 model LSTM Global...")

    # Tentukan URI server MLflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    print(f"[*] Menghubungkan ke MLflow server di: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)

    experiment_name = "Prediksi_Harga_Cabai_LSTM_Global"
    try:
        mlflow.create_experiment(experiment_name)
    except Exception:
        pass
    mlflow.set_experiment(experiment_name)

    # Aktifkan pencatatan otomatis TensorFlow / Keras oleh MLflow
    mlflow.tensorflow.autolog()

    os.makedirs("models", exist_ok=True)
    os.makedirs("scalers", exist_ok=True)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 1. Tahap 1: Pengambilan Data Mentah, Splitting, dan Imputasi
    print("[*] Tahap 1: Mengambil, membagi (Train/Test), dan membersihkan data per kombinasi dari database...")
    series_data_list = []
    all_train_prices = []

    for prov_idx, provinsi in enumerate(PROVINSI_LIST):
        for chili_idx, jenis in enumerate(JENIS_CABAI_LIST):
            # Mengambil data dari database tanpa filter harga IS NOT NULL
            # untuk mendapatkan data mentah dengan kemungkinan missing values
            cursor.execute(
                """
                SELECT tanggal, harga
                FROM data_harga_clean
                WHERE provinsi = %s AND jenis_cabai = %s
                ORDER BY tanggal ASC
                """,
                (provinsi, jenis)
            )
            rows = cursor.fetchall()
            if len(rows) < (LAG + 10):
                continue

            data = pd.DataFrame(rows)
            data["tanggal"] = pd.to_datetime(data["tanggal"])
            data = data.sort_values("tanggal").reset_index(drop=True)

            # Bersihkan harga format
            data["harga"] = data["harga"].apply(bersihkan_harga)

            # Split Train/Test (80:20) secara temporal sebelum interpolasi dan scaling
            n_train = int(len(data) * SPLIT_RATIO)
            train_df = data.iloc[:n_train].copy().reset_index(drop=True)
            test_df = data.iloc[n_train:].copy().reset_index(drop=True)

            # Lakukan interpolasi secara mandiri pada masing-masing split untuk mencegah leakage
            train_df = interpolasi_missing_value(train_df, provinsi, jenis)
            test_df = interpolasi_missing_value(test_df, provinsi, jenis)

            # Bulatkan harga setelah interpolasi ke 100 terdekat
            train_df["harga"] = (train_df["harga"] / 100).round() * 100
            test_df["harga"] = (test_df["harga"] / 100).round() * 100

            # Kumpulkan semua harga training untuk fit scaler global
            all_train_prices.extend(train_df["harga"].values)

            # Simpan data mentah ter-imputasi untuk diproses di Tahap 2 setelah scaler terbentuk
            series_data_list.append((train_df, test_df, prov_idx, chili_idx))

    cursor.close()
    connection.close()

    # 2. Tahap 2: Fitting Global Scaler menggunakan HANYA data train
    print("[*] Tahap 2: Fitting MinMaxScaler Global menggunakan hanya data Train...")
    all_train_prices = np.array(all_train_prices).reshape(-1, 1).astype(float)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(all_train_prices)
    joblib.dump(scaler, "scalers/global_scaler.save")
    print("[+] Scaler Global berhasil di-fit dan disimpan.")

    # 3. Tahap 3: Penskalaan, Pembuatan Supervised Lags
    print("[*] Tahap 3: Pemrosesan scaling, supervised lags")
    train_X_list, train_y_list = [], []
    test_X_list, test_y_list = [], []

    for train_df, test_df, prov_idx, chili_idx in series_data_list:
        # Scale data harga menggunakan global scaler yang di-fit di atas
        train_prices = train_df["harga"].values.reshape(-1, 1).astype(float)
        test_prices = test_df["harga"].values.reshape(-1, 1).astype(float)

        scaled_train = scaler.transform(train_prices)
        scaled_test = scaler.transform(test_prices)

        # Ubah ke supervised format lags sekuensial (Opsi B)
        # Train set
        reframed_train = series_to_supervised(scaled_train, LAG, 1)
        train_values = reframed_train.values
        train_x_raw, train_y = train_values[:, :-1], train_values[:, -1]

        # Test set (gabungkan dengan LAG terakhir dari train agar tidak memotong awal test set)
        test_input_seq = np.concatenate([scaled_train[-LAG:], scaled_test], axis=0)
        reframed_test = series_to_supervised(test_input_seq, LAG, 1)
        test_values = reframed_test.values
        test_x_raw, test_y = test_values[:, :-1], test_values[:, -1]

        # Reshape data x_raw menjadi 3D: [samples, LAG, 1]
        train_x_3d = train_x_raw.reshape((train_x_raw.shape[0], LAG, 1))
        test_x_3d = test_x_raw.reshape((test_x_raw.shape[0], LAG, 1))

        # Buat One-Hot Encoding array (panjang 38)
        prov_ohe = np.zeros(NUM_PROVINSI)
        prov_ohe[prov_idx] = 1.0

        chili_ohe = np.zeros(NUM_JENIS)
        chili_ohe[chili_idx] = 1.0

        ohe_features = np.concatenate([prov_ohe, chili_ohe]) # Panjang 38

        # Tile/Duplikasi OHE features sebanyak samples dan LAG -> shape: [samples, LAG, 38]
        train_ohe = np.tile(ohe_features, (len(train_x_3d), LAG, 1))
        test_ohe = np.tile(ohe_features, (len(test_x_3d), LAG, 1))

        # Gabungkan fitur harga dan OHE di dimensi fitur (axis=2) -> shape: [samples, LAG, 39]
        train_X = np.concatenate([train_x_3d, train_ohe], axis=2)
        test_X = np.concatenate([test_x_3d, test_ohe], axis=2)

        train_X_list.append(train_X)
        train_y_list.append(train_y)
        test_X_list.append(test_X)
        test_y_list.append(test_y)

    # Gabungkan semua data
    final_train_X = np.concatenate(train_X_list, axis=0)
    final_train_y = np.concatenate(train_y_list, axis=0)
    final_test_X = np.concatenate(test_X_list, axis=0)
    final_test_y = np.concatenate(test_y_list, axis=0)

    print(f"[+] Total data train: {final_train_X.shape[0]} baris")
    print(f"[+] Total data test: {final_test_X.shape[0]} baris")
    print(f"[+] Shape train input: {final_train_X.shape}") # (samples, 7, 39)
    print(f"[+] Shape test input: {final_test_X.shape}")   # (samples, 7, 39)

    run_name = "Run_Model_LSTM_Global"

    with mlflow.start_run(run_name=run_name) as run:
        print("[*] Melakukan fitting model LSTM Global...")

        model = Sequential([
            Input(shape=(final_train_X.shape[1], final_train_X.shape[2])),
            LSTM(LSTM_UNITS, return_sequences=False),
            Dense(1, activation='sigmoid')
        ])

        model.compile(loss='mse', optimizer='adam')

        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=25,
            restore_best_weights=True
        )

        history = model.fit(
            final_train_X, final_train_y,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_data=(final_test_X, final_test_y),
            callbacks=[early_stopping],
            verbose=1,
            shuffle=False
        )

        print("[*] Mengevaluasi performa model...")
        yhat = model.predict(final_test_X)
        yhat = np.clip(yhat, 0, 1)

        inv_yhat = scaler.inverse_transform(yhat)[:, 0]

        final_test_y_reshaped = final_test_y.reshape((len(final_test_y), 1))
        inv_y = scaler.inverse_transform(final_test_y_reshaped)[:, 0]

        mape = np.mean(np.abs((inv_y - inv_yhat) / inv_y)) * 100
        rmse = np.sqrt(mean_squared_error(inv_y, inv_yhat))
        mae = mean_absolute_error(inv_y, inv_yhat)

        final_loss = history.history['loss'][-1]

        # Log parameter kustom ke MLflow
        mlflow.log_param("lstm_units", LSTM_UNITS)
        mlflow.log_param("lag", LAG)
        mlflow.log_param("split_ratio", SPLIT_RATIO)
        mlflow.log_param("epochs", EPOCHS)
        mlflow.log_param("batch_size", BATCH_SIZE)
        mlflow.log_param("total_features", final_train_X.shape[2])

        # Log metrik evaluasi ke MLflow
        mlflow.log_metric("final_train_loss_mse", final_loss)
        mlflow.log_metric("global_mape", mape)
        mlflow.log_metric("global_rmse", rmse)
        mlflow.log_metric("global_mae", mae)

        # Simpan weights global
        model.save_weights("models/global_lstm.weights.h5")

        print("\n[✓] Model LSTM Global Tunggal Berhasil Dilatih!")
        print(f"    RMSE  : {rmse:.2f}")
        print(f"    MAE   : {mae:.2f}")
        print(f"    MAPE  : {mape:.2f}%")
        print(f"    Run ID: {run.info.run_id}")


if __name__ == "__main__":
    main()
