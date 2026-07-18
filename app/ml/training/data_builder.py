"""
Data builder untuk supervised learning dari time series.

Mengubah data time series harga cabai menjadi format
[X_train, y_train, X_test, y_test] dengan sliding window lags,
One-Hot Encoding, dan global scaling.
"""

import numpy as np
import pandas as pd


def series_to_supervised(
    data: np.ndarray,
    n_in: int = 1,
    n_out: int = 1,
    dropnan: bool = True,
) -> pd.DataFrame:
    """
    Ubah array time series menjadi format supervised learning.

    Setiap baris output berisi nilai t-n, ..., t-1 (input)
    dan t (target yang akan diprediksi).

    Args:
        data: Array 1D atau 2D (n_samples, n_features).
        n_in: Jumlah lag timestep sebagai input.
        n_out: Jumlah timestep ke depan sebagai output.
        dropnan: Hapus baris yang mengandung NaN setelah shifting.

    Returns:
        pd.DataFrame dengan kolom penamaan var{i}(t-{lag}) dan var{i}(t+{lead}).
    """
    n_vars = 1 if len(data.shape) == 1 else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = [], []

    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [f"var{j + 1}(t-{i})" for j in range(n_vars)]

    for i in range(n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [f"var{j + 1}(t)" for j in range(n_vars)]
        else:
            names += [f"var{j + 1}(t+{i})" for j in range(n_vars)]

    agg = pd.concat(cols, axis=1)
    agg.columns = names
    if dropnan:
        agg.dropna(inplace=True)
    return agg


def build_feature_tensor(
    price_array: np.ndarray,
    prov_ohe: np.ndarray,
    chili_ohe: np.ndarray,
    lag: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Bangun tensor fitur 3D dari array harga ter-scale dan OHE.

    Args:
        price_array: Array harga ter-scale, shape (n_samples, 1).
        prov_ohe: OHE provinsi, shape (n_provinsi,).
        chili_ohe: OHE jenis cabai, shape (n_jenis,).
        lag: Jumlah timestep input model.

    Returns:
        Tuple (X, y):
        - X: shape (samples, lag, 1 + n_prov + n_jenis).
        - y: shape (samples,).
    """
    reframed = series_to_supervised(price_array, lag, 1)
    values = reframed.values
    x_raw, y = values[:, :-1], values[:, -1]

    # Reshape ke 3D: [samples, lag, 1]
    x_3d = x_raw.reshape((x_raw.shape[0], lag, 1))

    # Gabungkan OHE features
    ohe = np.concatenate([prov_ohe, chili_ohe])  # (n_prov + n_jenis,)
    ohe_tiled = np.tile(ohe, (len(x_3d), lag, 1))  # (samples, lag, 38)

    # Gabungkan harga dan OHE di dimensi fitur
    X = np.concatenate([x_3d, ohe_tiled], axis=2)  # (samples, lag, 39)

    return X, y
