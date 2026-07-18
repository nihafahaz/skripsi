"""
Service untuk prediksi harga cabai.

Mengorkestrasikan seluruh proses prediksi:
1. Validasi input (provinsi dan jenis cabai)
2. Ambil data historis dari repository
3. Terapkan LOCF untuk gap akhir pekan / hari libur
4. Bangun input tensor
5. Jalankan prediksi multi-step
6. Kembalikan hasil terstruktur

Backend (endpoint) hanya memanggil satu method dari service ini
dan tidak perlu mengetahui detail implementasi ML.
"""

from app.core.exceptions import InvalidInputException
from app.core.logger import get_logger
from app.db.repositories.price_repository import PriceRepository
from app.ml.inference.model_loader import get_model_loader
from app.ml.inference.preprocessor import apply_locf, build_input_tensor
from app.ml.inference.predictor import predict_multi_step
from app.utils.constants import JENIS_CABAI_LIST, LAG, PROVINSI_LIST

logger = get_logger(__name__)

# Singleton repository instance
_price_repo = PriceRepository()


def run_prediction(
    provinsi: str,
    jenis_cabai: str,
    durasi: int,
) -> dict:
    """
    Jalankan prediksi harga cabai dan kembalikan hasilnya.

    Args:
        provinsi: Nama provinsi (harus ada di PROVINSI_LIST).
        jenis_cabai: Jenis cabai (harus ada di JENIS_CABAI_LIST).
        durasi: Jumlah hari ke depan yang akan diprediksi (1–30).

    Returns:
        Dict berisi:
        - provinsi, jenis_cabai, durasi
        - harga_terakhir: harga historis terakhir
        - tanggal_terakhir: tanggal historis terakhir (YYYY-MM-DD)
        - data: list dict {'tanggal', 'harga'} hasil prediksi

    Raises:
        InvalidInputException: Jika provinsi atau jenis cabai tidak valid.
        InsufficientDataException: Jika data historis kurang dari LAG.
        DatabaseException: Jika gagal mengambil data dari database.
        MLModelException: Jika inferensi model gagal.
    """
    # --- Validasi input ---
    if provinsi not in PROVINSI_LIST:
        raise InvalidInputException(
            message=f"Provinsi '{provinsi}' tidak dikenali.",
            detail=f"Daftar provinsi valid: {PROVINSI_LIST}",
        )

    if jenis_cabai not in JENIS_CABAI_LIST:
        raise InvalidInputException(
            message=f"Jenis cabai '{jenis_cabai}' tidak dikenali.",
            detail=f"Daftar jenis cabai valid: {JENIS_CABAI_LIST}",
        )

    logger.info("Prediksi: %s / %s | durasi=%d", provinsi, jenis_cabai, durasi)

    # --- Ambil data historis ---
    data_historis = _price_repo.get_recent_prices_for_prediction(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        lag=LAG,
    )

    # --- LOCF untuk gap akhir pekan ---
    data_historis = apply_locf(data_historis, lag=LAG)

    # --- Bangun input tensor ---
    loader = get_model_loader()
    input_tensor, ohe_features, tanggal_terakhir, harga_terakhir = build_input_tensor(
        data_historis=data_historis,
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        scaler=loader.scaler,
    )

    # --- Prediksi multi-step ---
    hasil = predict_multi_step(
        model=loader.model,
        scaler=loader.scaler,
        initial_tensor=input_tensor,
        ohe_features=ohe_features,
        tanggal_terakhir=tanggal_terakhir,
        durasi=durasi,
    )

    return {
        "provinsi": provinsi,
        "jenis_cabai": jenis_cabai,
        "durasi": durasi,
        "harga_terakhir": harga_terakhir,
        "tanggal_terakhir": tanggal_terakhir.strftime("%Y-%m-%d"),
        "data": hasil,
    }
