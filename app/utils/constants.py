"""
Konstanta global aplikasi prediksi harga cabai.

Ini adalah SATU-SATUNYA sumber kebenaran untuk semua konstanta domain.
Semua modul lain harus mengimpor dari sini — tidak boleh mendefinisikan ulang.
"""

# Lag time window yang digunakan model LSTM (7 hari terakhir)
LAG: int = 7

# Daftar provinsi yang didukung (sudah di-sort)
PROVINSI_LIST: list[str] = sorted([
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

# Daftar jenis cabai yang didukung (sudah di-sort)
JENIS_CABAI_LIST: list[str] = sorted([
    'Cabai Merah Besar',
    'Cabai Merah Keriting',
    'Cabai Rawit Hijau',
    'Cabai Rawit Merah',
])

# Derived constants
NUM_PROVINSI: int = len(PROVINSI_LIST)   # 34
NUM_JENIS: int = len(JENIS_CABAI_LIST)    # 4
# Total fitur input model = 1 (harga_scaled) + 34 (OHE provinsi) + 4 (OHE jenis) = 39
NUM_FEATURES: int = 1 + NUM_PROVINSI + NUM_JENIS

# Pasangan jenis cabai yang saling mengikuti pola harga
PASANGAN_CABAI: dict[str, str] = {
    'Cabai Rawit Hijau': 'Cabai Rawit Merah',
    'Cabai Rawit Merah': 'Cabai Rawit Hijau',
    'Cabai Merah Keriting': 'Cabai Merah Besar',
    'Cabai Merah Besar': 'Cabai Merah Keriting',
}
