import os
import numpy as np
import pandas as pd
import mlflow
import mlflow.tensorflow
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import joblib

def main():
    print("[*] Memulai pencatatan training model LSTM dengan MLflow...")
    
    # Tentukan URI server MLflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    print(f"[*] Menghubungkan ke MLflow server di: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)
    
    experiment_name = "Prediksi_Harga_Cabai_LSTM"
    try:
        mlflow.create_experiment(experiment_name)
    except Exception:
        # Experiment sudah terdaftar
        pass
    mlflow.set_experiment(experiment_name)
    
    # Aktifkan pencatatan otomatis TensorFlow / Keras oleh MLflow
    mlflow.tensorflow.autolog()
    
    # Generate data harga cabai simulasi (Jawa Barat - Cabai Rawit Merah)
    np.random.seed(42)
    data_size = 100
    base_price = 40000
    noise = np.random.normal(0, 2000, data_size)
    trend = np.linspace(0, 10000, data_size)
    prices = base_price + trend + noise
    
    # Normalisasi Data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_prices = scaler.fit_transform(prices.reshape(-1, 1))
    
    # Siapkan data time-series (Lag = 1)
    X, y = [], []
    for i in range(len(scaled_prices) - 1):
        X.append(scaled_prices[i])
        y.append(scaled_prices[i + 1])
    X, y = np.array(X), np.array(y)
    
    # Ubah dimensi input menjadi format Keras: [samples, time steps, features]
    X = X.reshape((X.shape[0], 1, 1))
    
    epochs = 15
    batch_size = 8
    lstm_units = 32
    
    # Memulai session run MLflow
    with mlflow.start_run(run_name="Run_Jawa_Barat_Cabai_Rawit_Merah") as run:
        # Membangun model LSTM sesuai arsitektur main.py
        model = Sequential()
        model.add(LSTM(lstm_units, input_shape=(1, 1)))
        model.add(Dense(1, activation='sigmoid'))
        model.compile(loss='mse', optimizer='adam')
        
        print("[*] Melakukan fitting model LSTM...")
        history = model.fit(
            X, y, 
            epochs=epochs, 
            batch_size=batch_size, 
            verbose=1, 
            shuffle=False
        )
        
        final_loss = history.history['loss'][-1]
        
        # Log parameter kustom ke MLflow Dashboard
        mlflow.log_param("lstm_units", lstm_units)
        mlflow.log_param("lag", 1)
        mlflow.log_param("provinsi", "Jawa Barat")
        mlflow.log_param("jenis_cabai", "Cabai Rawit Merah")
        
        # Log metrik evaluasi ke MLflow Dashboard
        mlflow.log_metric("final_train_loss_mse", final_loss)
        
        # Simpan weights & scaler lokal untuk FastAPI (opsional)
        os.makedirs("models", exist_ok=True)
        os.makedirs("scalers", exist_ok=True)
        
        model_name = "Jawa Barat_Cabai Rawit Merah"
        model.save_weights(f"models/{model_name}.weights.h5")
        joblib.dump(scaler, f"scalers/{model_name}_scaler.save")
        
        print("[+] Model berhasil dilatih, disimpan, dan terdaftar di server MLflow!")
        print(f"Run ID: {run.info.run_id}")

if __name__ == "__main__":
    main()
