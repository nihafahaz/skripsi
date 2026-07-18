"""Endpoint prediksi harga cabai."""

from fastapi import APIRouter
from app.api.v1.schemas.prediction import PredictRequest, PredictResponse
from app.services.prediction_service import run_prediction

router = APIRouter(prefix="/predict", tags=["Prediksi"])


@router.post(
    "",
    summary="Prediksi harga cabai",
    response_model=PredictResponse,
)
def predict(request: PredictRequest) -> dict:
    """
    Jalankan prediksi harga cabai menggunakan model LSTM Global.

    Model memprediksi harga untuk `durasi` hari ke depan berdasarkan
    data historis 7 hari terakhir dari database.

    - **provinsi**: Nama provinsi Indonesia (34 provinsi didukung).
    - **jenis_cabai**: Jenis komoditas (Cabai Merah Besar, Cabai Rawit Merah, dll.).
    - **durasi**: Jumlah hari prediksi (1–30 hari).
    """
    result = run_prediction(
        provinsi=request.provinsi,
        jenis_cabai=request.jenis_cabai,
        durasi=request.durasi,
    )
    return {"status": "success", **result}
