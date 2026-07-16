import os
import sys
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt

# Tambahkan path backend
sys.path.append(r"c:\Users\Hanifah Az-Zahra\AndroidStudioProjects\backend")

from train_mlflow import PROVINSI_LIST, JENIS_CABAI_LIST, LAG, SPLIT_RATIO, series_to_supervised
from preprocessing import interpolasi_missing_value, bersihkan_harga
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

# Fungsi display fallback jika dijalankan di terminal biasa (bukan Jupyter)
try:
    from IPython.display import display
except ImportError:
    display = print

# Baca file hasil evaluasi
excel_file = "evaluasi_model_global_per_komoditas.xlsx"
df_results = pd.read_excel(excel_file)

# Samakan nama kolom ke lowercase agar sesuai dengan skrip Anda
df_results = df_results.rename(columns={
    "RMSE": "rmse",
    "MAE": "mae",
    "MAPE (%)": "mape"
})

# Jalankan kode analisis statistik Anda
print("=== DESKRIPSI STATISTIK MODEL GLOBAL ===")
print(df_results.describe())

print("\n=== KLASIFIKASI TINGKAT ERROR MAPE ===")
print("MAPE < 10% :", (df_results["mape"] < 10).sum())
print("10-20% :", ((df_results["mape"] >= 10) & (df_results["mape"] < 20)).sum())
print("20-50% :", ((df_results["mape"] >= 20) & (df_results["mape"] < 50)).sum())
print(">50% :", (df_results["mape"] >= 50).sum())

print("\n=== TOP 10 WILAYAH/KOMODITAS TERBAIK (MAPE TERKECIL) ===")
display(df_results.sort_values("mape").head(10))

print("\n=== TOP 10 WILAYAH/KOMODITAS TERBURUK (MAPE TERBESAR) ===")
display(df_results.sort_values("mape", ascending=False).head(10))


def plot_prediksi_vs_aktual(provinsi, jenis):
    print(f"\n[*] Mengambil data dan melakukan prediksi untuk {provinsi} - {jenis}...")
    
    # 1. Load model global dan scaler
    model = Sequential([
        Input(shape=(LAG, 39)),
        LSTM(32, return_sequences=False),
        Dense(1, activation='sigmoid')
    ])
    model.load_weights("models/global_lstm.weights.h5")
    scaler = joblib.load("scalers/global_scaler.save")
    
    # 2. Baca file Excel
    split_dir = "split"
    filename = f"{provinsi}_{jenis}.xlsx"
    filepath = os.path.join(split_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"[-] ERROR: File {filepath} tidak ditemukan!")
        return

    data = pd.read_excel(filepath)
    if "date" in data.columns:
        data = data.rename(columns={"date": "tanggal"})
    data["tanggal"] = pd.to_datetime(data["tanggal"])
    data = data.sort_values("tanggal").reset_index(drop=True)
    data["harga"] = data["harga"].apply(bersihkan_harga)

    # 3. Split Train/Test (80:20)
    n_train = int(len(data) * SPLIT_RATIO)
    train_df = data.iloc[:n_train].copy().reset_index(drop=True)
    test_df = data.iloc[n_train:].copy().reset_index(drop=True)

    # 4. Interpolasi secara terpisah sesuai aturan baru
    train_df = interpolasi_missing_value(train_df, provinsi, jenis)
    test_df = interpolasi_missing_value(test_df, provinsi, jenis)

    # Bulatkan harga
    train_df["harga"] = (train_df["harga"] / 100).round() * 100
    test_df["harga"] = (test_df["harga"] / 100).round() * 100

    # Scale data
    train_prices = train_df["harga"].values.reshape(-1, 1).astype(float)
    test_prices = test_df["harga"].values.reshape(-1, 1).astype(float)

    scaled_train = scaler.transform(train_prices)
    scaled_test = scaler.transform(test_prices)

    # 5. Buat supervised sequence dengan history Train terakhir
    test_input_seq = np.concatenate([scaled_train[-LAG:], scaled_test], axis=0)
    reframed_test = series_to_supervised(test_input_seq, LAG, 1)
    test_values = reframed_test.values
    test_x_raw, test_y = test_values[:, :-1], test_values[:, -1]

    # Reshape ke 3D
    test_x_3d = test_x_raw.reshape((test_x_raw.shape[0], LAG, 1))

    # One-Hot Encoding
    prov_idx = PROVINSI_LIST.index(provinsi)
    chili_idx = JENIS_CABAI_LIST.index(jenis)
    
    prov_ohe = np.zeros(len(PROVINSI_LIST))
    prov_ohe[prov_idx] = 1.0
    chili_ohe = np.zeros(len(JENIS_CABAI_LIST))
    chili_ohe[chili_idx] = 1.0
    ohe_features = np.concatenate([prov_ohe, chili_ohe])

    test_ohe = np.tile(ohe_features, (len(test_x_3d), LAG, 1))
    test_X = np.concatenate([test_x_3d, test_ohe], axis=2)

    # 6. Prediksi
    yhat = model.predict(test_X, verbose=0)
    yhat = np.clip(yhat, 0, 1)

    # Inverse transform
    inv_yhat = scaler.inverse_transform(yhat)[:, 0]
    inv_y = test_prices[:, 0]
    
    # Ambil tanggal untuk sumbu X
    dates = test_df["tanggal"].values

    # 7. Plotting
    plt.figure(figsize=(15, 6))
    plt.plot(dates, inv_y, label="Harga Aktual", color="blue", linewidth=2)
    plt.plot(dates, inv_yhat, label="Harga Prediksi", color="orange", linestyle="--", linewidth=2)

    plt.title(f"Grafik Prediksi vs Aktual: {provinsi} - {jenis}", fontsize=14, pad=15)
    plt.xlabel("Tanggal", fontsize=12)
    plt.ylabel("Harga (Rp/kg)", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.gcf().autofmt_xdate() # Memiringkan format tanggal agar rapi

    # Simpan plot ke file gambar
    output_img = f"grafik_{provinsi.replace(' ', '_')}_{jenis.replace(' ', '_')}.png"
    plt.savefig(output_img, dpi=300, bbox_inches="tight")
    print(f"[+] Grafik berhasil disimpan ke: {output_img}")
    
    plt.show()

# Panggil fungsi plotting untuk provinsi dan komoditas pilihan
plot_prediksi_vs_aktual("DKI Jakarta", "Cabai Merah Keriting")
