"""Endpoint download laporan PDF prediksi harga cabai."""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.report_service import generate_prediction_pdf

router = APIRouter(prefix="/download", tags=["Laporan PDF"])


@router.get("", summary="Download laporan prediksi PDF")
def download_report(
    provinsi: str,
    jenis_cabai: str,
    durasi: int,
) -> FileResponse:
    """
    Generate dan download laporan prediksi harga cabai dalam format PDF.

    Parameter sama dengan endpoint `/predict`.
    File PDF akan di-download langsung oleh browser/klien.
    """
    pdf_path = generate_prediction_pdf(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        durasi=durasi,
    )

    return FileResponse(
        path=pdf_path,
        filename="hasil_prediksi.pdf",
        media_type="application/pdf",
        background=None,
    )
