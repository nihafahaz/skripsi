"""Pydantic schemas untuk endpoint prediksi harga cabai."""

from pydantic import BaseModel, Field, field_validator
from app.utils.constants import PROVINSI_LIST, JENIS_CABAI_LIST


class PredictRequest(BaseModel):
    """Request body untuk endpoint POST /predict dan GET /download."""

    provinsi: str = Field(..., description="Nama provinsi Indonesia.")
    jenis_cabai: str = Field(..., description="Jenis komoditas cabai.")
    durasi: int = Field(
        ..., ge=1, le=30, description="Jumlah hari prediksi ke depan (1–30)."
    )

    @field_validator("provinsi")
    @classmethod
    def validate_provinsi(cls, v: str) -> str:
        if v not in PROVINSI_LIST:
            raise ValueError(
                f"Provinsi '{v}' tidak dikenali. "
                f"Pilih salah satu dari: {PROVINSI_LIST}"
            )
        return v

    @field_validator("jenis_cabai")
    @classmethod
    def validate_jenis_cabai(cls, v: str) -> str:
        if v not in JENIS_CABAI_LIST:
            raise ValueError(
                f"Jenis cabai '{v}' tidak dikenali. "
                f"Pilih salah satu dari: {JENIS_CABAI_LIST}"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "provinsi": "DKI Jakarta",
                "jenis_cabai": "Cabai Rawit Merah",
                "durasi": 7,
            }
        }
    }


class PredictDataPoint(BaseModel):
    """Satu titik data hasil prediksi."""
    tanggal: str
    harga: int


class PredictResponse(BaseModel):
    """Response body untuk endpoint prediksi."""
    status: str = "success"
    provinsi: str
    jenis_cabai: str
    durasi: int
    harga_terakhir: float
    tanggal_terakhir: str
    data: list[PredictDataPoint]
