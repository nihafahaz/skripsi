"""
Training standalone dari folder split/ (tanpa MySQL).

Menggunakan file {Provinsi}_{Jenis Cabai}.xlsx dari folder split/
sebagai sumber data, lalu melatih model LSTM Global dan menyimpan
weights + scaler ke folder models/ dan scalers/.

Cara pakai:
    python scripts/train_from_split.py
"""

import os
import sys
import time
import warnings
import glob

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

# --- Path setup ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.callbacks import EarlyStopping

tf.random.set_seed(42)
np.random.seed(42)

# ── Konfigurasi (sesuai eksperimen terbaik) ─────────────────────────────────
SPLIT_DIR    = os.path.join(ROOT_DIR, "split")
MODEL_PATH   = os.path.join(ROOT_DIR, "models", "lstm_global.weights.h5")
SCALER_PATH  = os.path.join(ROOT_DIR, "scalers", "global_scaler.save")
PLOT_PATH    = os.path.join(ROOT_DIR, "models", "prediksi_vs_aktual.png")

SPLIT_RATIO  = 0.70    # 70:30
MAX_EPOCHS   = 150
PATIENCE     = 20
MIN_DELTA    = 0.0001
LSTM_UNITS   = 32
BATCH_SIZE   = 32
LAG          = 7
# ────────────────────────────────────────────────────────────────────────────

PROVINSI_LIST = sorted([
    'Aceh', 'Bali', 'Banten', 'Bengkulu', 'DI Yogyakarta', 'DKI Jakarta',
    'Gorontalo', 'Jambi', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur',
    'Kalimantan Barat', 'Kalimantan Selatan', 'Kalimantan Tengah',
    'Kalimantan Timur', 'Kalimantan Utara', 'Kepulauan Bangka Belitung',
    'Kepulauan Riau', 'Lampung', 'Maluku', 'Maluku Utara',
    'Nusa Tenggara Barat', 'Nusa Tenggara Timur', 'Papua', 'Papua Barat',
    'Riau', 'Sulawesi Barat', 'Sulawesi Selatan', 'Sulawesi Tengah',
    'Sulawesi Tenggara', 'Sulawesi Utara', 'Sumatera Barat',
    'Sumatera Selatan', 'Sumatera Utara',
])
JENIS_CABAI_LIST = sorted([
    'Cabai Merah Besar', 'Cabai Merah Keriting',
    'Cabai Rawit Hijau', 'Cabai Rawit Merah',
])
NUM_PROVINSI = len(PROVINSI_LIST)
NUM_JENIS    = len(JENIS_CABAI_LIST)


# ── Preprocessing ────────────────────────────────────────────────────────────

def clean_price(nilai):
    if pd.isna(nilai): return None
    if isinstance(nilai, (int, float, np.integer, np.floating)): return float(nilai)
    nilai = str(nilai).strip()
    if nilai in ('', '-', 'nan', 'None'): return None
    return pd.to_numeric(str(nilai).replace(',', '').replace('.', ''), errors='coerce')


def interpolate_missing(data, label=''):
    data = data.copy()
    non_nan = data[data['harga'].notna()].index
    if len(non_nan) < 2:
        data['harga'] = data['harga'].interpolate(method='linear', limit_direction='both').bfill().ffill()
        return data
    fi, li = non_nan[0], non_nan[-1]
    inside = data.loc[fi:li, 'harga']
    if inside.isna().any():
        try:
            interp = inside.interpolate(method='spline', order=3)
            if (interp < 0).any() or (interp > 500_000).any() or interp.isna().any():
                raise ValueError()
            data.loc[fi:li, 'harga'] = interp
        except Exception:
            data.loc[fi:li, 'harga'] = inside.interpolate(method='linear')
    data['harga'] = data['harga'].interpolate(method='linear', limit_direction='both').bfill().ffill()
    return data


def parse_filename(stem):
    for prov in PROVINSI_LIST:
        if stem.startswith(prov + '_'):
            remainder = stem[len(prov) + 1:]
            if remainder in JENIS_CABAI_LIST:
                return prov, remainder
    return None, None


def series_to_supervised(data, n_in, n_out=1, dropnan=True):
    df = pd.DataFrame(data)
    cols = []
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
    for i in range(n_out):
        cols.append(df.shift(-i))
    agg = pd.concat(cols, axis=1)
    if dropnan:
        agg.dropna(inplace=True)
    return agg


def build_feature_tensor(price_array, prov_ohe, chili_ohe, lag):
    reframed = series_to_supervised(price_array, lag, 1)
    values   = reframed.values
    x_raw, y = values[:, :-1], values[:, -1]
    x_3d     = x_raw.reshape((x_raw.shape[0], lag, 1))
    ohe      = np.concatenate([prov_ohe, chili_ohe])
    ohe_tile = np.tile(ohe, (len(x_3d), lag, 1))
    return np.concatenate([x_3d, ohe_tile], axis=2), y


# ── Load data ────────────────────────────────────────────────────────────────

def load_series():
    files = [
        f for f in sorted(glob.glob(os.path.join(SPLIT_DIR, '*.xlsx')))
        if not f.endswith('_train.xlsx') and not f.endswith('_test.xlsx')
    ]
    print(f"   Ditemukan {len(files)} file xlsx")

    series_list = []
    skip_nm = skip_sh = skip_err = 0
    for fpath in files:
        stem  = os.path.basename(fpath).replace('.xlsx', '')
        prov, jenis = parse_filename(stem)
        if prov is None:
            skip_nm += 1; continue
        try:
            df = pd.read_excel(fpath)
            df.columns = [c.lower().strip() for c in df.columns]
            col_t = next((c for c in df.columns if 'tanggal' in c or 'date' in c or 'tgl' in c), None)
            col_h = next((c for c in df.columns if 'harga' in c or 'price' in c), None)
            if col_t is None or col_h is None:
                skip_err += 1; continue
            df = df[[col_t, col_h]].rename(columns={col_t: 'tanggal', col_h: 'harga'})
            df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
            df = df.dropna(subset=['tanggal']).sort_values('tanggal').reset_index(drop=True)
            df['harga'] = df['harga'].apply(clean_price)
            if len(df) < LAG + 20:
                skip_sh += 1; continue
            series_list.append({
                'provinsi' : prov, 'jenis': jenis,
                'prov_idx' : PROVINSI_LIST.index(prov),
                'jenis_idx': JENIS_CABAI_LIST.index(jenis),
                'data'     : df,
            })
        except Exception as e:
            print(f"   ⚠ Error {stem}: {e}"); skip_err += 1

    print(f"   Berhasil: {len(series_list)} | Skip nama: {skip_nm} | Pendek: {skip_sh} | Error: {skip_err}")
    return series_list


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()
    print("=" * 65)
    print("  TRAINING MODEL LSTM GLOBAL")
    print(f"  Split: {int(SPLIT_RATIO*100)}:{int((1-SPLIT_RATIO)*100)} | "
          f"Epoch: {MAX_EPOCHS} | Patience: {PATIENCE}")
    print("=" * 65)

    os.makedirs(os.path.dirname(MODEL_PATH),  exist_ok=True)
    os.makedirs(os.path.dirname(SCALER_PATH), exist_ok=True)

    # ── 1. Load data ──
    print("\n[1/5] Memuat data dari split/...")
    series_list = load_series()
    if not series_list:
        print("❌ Tidak ada data! Cek folder split/")
        return

    # ── 2. Split + preprocessing ──
    print(f"\n[2/5] Split {int(SPLIT_RATIO*100)}:{int((1-SPLIT_RATIO)*100)} + interpolasi + pembulatan...")
    all_train_prices = []
    segments         = []
    for s in series_list:
        n = int(len(s['data']) * SPLIT_RATIO)

        # Split dulu
        train_df = s['data'].iloc[:n].copy().reset_index(drop=True)
        test_df  = s['data'].iloc[n:].copy().reset_index(drop=True)

        # Interpolasi terpisah
        train_df = interpolate_missing(train_df, 'train')
        test_df  = interpolate_missing(test_df,  'test')

        # Pembulatan
        train_df['harga'] = (train_df['harga'] / 100).round() * 100
        test_df['harga']  = (test_df['harga']  / 100).round() * 100

        if len(train_df) < LAG + 5 or len(test_df) < 2:
            continue

        all_train_prices.extend(train_df['harga'].dropna().values)
        segments.append((train_df, test_df, s['prov_idx'], s['jenis_idx'],
                         s['provinsi'], s['jenis']))

    print(f"   Segment siap: {len(segments)}")

    # ── 3. Fit scaler ──
    print("\n[3/5] Fitting MinMaxScaler dari data train...")
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(np.array(all_train_prices, dtype=float).reshape(-1, 1))
    joblib.dump(scaler, SCALER_PATH)
    print(f"   Scaler disimpan → {SCALER_PATH}")

    # ── 4. Build tensor ──
    print("\n[4/5] Membangun feature tensor...")
    trX_l, trY_l, teX_l, teY_l = [], [], [], []
    meta_test = []  # simpan info untuk plot per provinsi/jenis

    for train_df, test_df, prov_idx, jenis_idx, prov, jenis in segments:
        tr_p = scaler.transform(train_df['harga'].values.reshape(-1, 1).astype(float))
        te_p = scaler.transform(test_df['harga'].values.reshape(-1, 1).astype(float))
        po   = np.eye(NUM_PROVINSI)[prov_idx]
        jo   = np.eye(NUM_JENIS)[jenis_idx]

        X_tr, y_tr = build_feature_tensor(tr_p, po, jo, LAG)
        X_te, y_te = build_feature_tensor(np.concatenate([tr_p[-LAG:], te_p]), po, jo, LAG)

        trX_l.append(X_tr); trY_l.append(y_tr)
        teX_l.append(X_te); teY_l.append(y_te)
        meta_test.append((prov, jenis, len(y_te)))

    trX = np.concatenate(trX_l); trY = np.concatenate(trY_l)
    teX = np.concatenate(teX_l); teY = np.concatenate(teY_l)
    print(f"   Train: {trX.shape} | Test: {teX.shape}")

    # ── 5. Training ──
    print(f"\n[5/5] Training LSTM {LSTM_UNITS} units...")
    model = Sequential([
        Input(shape=(trX.shape[1], trX.shape[2])),
        LSTM(LSTM_UNITS, return_sequences=False),
        Dense(1, activation='sigmoid'),
    ])
    model.compile(loss='mse', optimizer='adam')

    es = EarlyStopping(monitor='val_loss', patience=PATIENCE, min_delta=MIN_DELTA, restore_best_weights=True)
    t0 = time.time()
    hist = model.fit(
        trX, trY, epochs=MAX_EPOCHS, batch_size=BATCH_SIZE,
        validation_data=(teX, teY), callbacks=[es],
        verbose=1, shuffle=False,
    )
    train_time = time.time() - t0
    best_epoch = len(hist.history['loss'])

    model.save_weights(MODEL_PATH)
    print(f"\n   Weights disimpan → {MODEL_PATH}")

    # ── Evaluasi ──
    y_pred   = np.clip(model.predict(teX, verbose=0), 0, 1)
    inv_pred = scaler.inverse_transform(y_pred)[:, 0]
    inv_true = scaler.inverse_transform(teY.reshape(-1, 1))[:, 0]

    mask = inv_true != 0
    mape = float(np.mean(np.abs((inv_true[mask] - inv_pred[mask]) / inv_true[mask])) * 100)
    rmse = float(np.sqrt(mean_squared_error(inv_true, inv_pred)))
    mae  = float(mean_absolute_error(inv_true, inv_pred))

    total_time = time.time() - t_start

    # ── Statistik ──
    print("\n" + "=" * 65)
    print("  HASIL TRAINING")
    print("=" * 65)
    print(f"  MAPE             : {mape:.4f}%")
    print(f"  RMSE             : Rp {rmse:,.0f}")
    print(f"  MAE              : Rp {mae:,.0f}")
    print(f"  Epoch (best/max) : {best_epoch}/{MAX_EPOCHS}")
    print(f"  Waktu training   : {train_time:.1f}s")
    print(f"  Waktu total      : {total_time:.1f}s")
    print(f"  Split            : {int(SPLIT_RATIO*100)}:{int((1-SPLIT_RATIO)*100)}")
    print(f"  Patience         : {PATIENCE}")
    print(f"  Segmen           : {len(segments)} (provinsi × jenis)")
    print("=" * 65)

    # ── Plot prediksi vs aktual ──
    print("\n  Membuat grafik prediksi vs aktual...")

    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor('#0F172A')
    gs  = gridspec.GridSpec(3, 1, figure=fig, hspace=0.45)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor('#1E293B')
        for spine in ax.spines.values():
            spine.set_color('#334155')

    # Panel 1: Prediksi vs aktual (sample 300)
    n_show = min(300, len(inv_true))
    ax1.plot(inv_true[:n_show], color='#60A5FA', lw=1.8, label='Harga Aktual', alpha=0.9)
    ax1.plot(inv_pred[:n_show], color='#F472B6', lw=1.5, ls='--', label='Prediksi LSTM', alpha=0.9)
    ax1.fill_between(range(n_show), inv_true[:n_show], inv_pred[:n_show],
                     alpha=0.08, color='#818CF8')
    ax1.set_title('Prediksi vs Aktual Harga Cabai (Global LSTM)',
                  color='#F1F5F9', fontsize=13, fontweight='bold', pad=10)
    ax1.set_xlabel('Sample Index', color='#94A3B8', fontsize=10)
    ax1.set_ylabel('Harga (Rp)', color='#94A3B8', fontsize=10)
    ax1.tick_params(colors='#94A3B8')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'Rp {x:,.0f}'))
    ax1.legend(facecolor='#1E293B', labelcolor='#F1F5F9', fontsize=10, loc='upper right')
    ax1.grid(color='#334155', lw=0.5, alpha=0.5)

    # Panel 2: Residual error
    residual = inv_true[:n_show] - inv_pred[:n_show]
    colors   = ['#34D399' if r >= 0 else '#F87171' for r in residual]
    ax2.bar(range(n_show), residual, color=colors, alpha=0.7, width=1.0)
    ax2.axhline(0, color='#94A3B8', lw=1, ls='--')
    ax2.set_title('Residual Error (Aktual − Prediksi)',
                  color='#F1F5F9', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('Sample Index', color='#94A3B8', fontsize=10)
    ax2.set_ylabel('Error (Rp)', color='#94A3B8', fontsize=10)
    ax2.tick_params(colors='#94A3B8')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'Rp {x:,.0f}'))
    ax2.grid(color='#334155', lw=0.5, alpha=0.5, axis='y')

    # Panel 3: Kurva training loss
    ax3.plot(hist.history['loss'],     color='#60A5FA', lw=2, label='Train Loss')
    ax3.plot(hist.history['val_loss'], color='#F472B6', lw=2, ls='--', label='Val Loss')
    ax3.axvline(best_epoch - 1, color='#FBBF24', ls=':', lw=1.5,
                label=f'Best Epoch ({best_epoch})')
    ax3.set_title('Kurva Training Loss (MSE)',
                  color='#F1F5F9', fontsize=12, fontweight='bold', pad=10)
    ax3.set_xlabel('Epoch', color='#94A3B8', fontsize=10)
    ax3.set_ylabel('MSE Loss', color='#94A3B8', fontsize=10)
    ax3.tick_params(colors='#94A3B8')
    ax3.legend(facecolor='#1E293B', labelcolor='#F1F5F9', fontsize=10)
    ax3.grid(color='#334155', lw=0.5, alpha=0.5)

    # Anotasi statistik
    stats_text = (
        f"MAPE: {mape:.2f}%   |   RMSE: Rp {rmse:,.0f}   |   "
        f"MAE: Rp {mae:,.0f}   |   Epoch: {best_epoch}/{MAX_EPOCHS}   |   "
        f"Split: {int(SPLIT_RATIO*100)}:{int((1-SPLIT_RATIO)*100)}"
    )
    fig.text(0.5, 0.01, stats_text, ha='center', color='#94A3B8', fontsize=10,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#1E293B', edgecolor='#334155'))

    plt.savefig(PLOT_PATH, dpi=150, bbox_inches='tight', facecolor='#0F172A')
    plt.close()
    print(f"  Grafik disimpan → {PLOT_PATH}")
    print("\n✅ Training selesai!")


if __name__ == "__main__":
    main()
