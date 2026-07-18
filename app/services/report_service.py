"""
Service untuk pembuatan laporan PDF prediksi harga cabai.

Menggabungkan hasil prediksi dari prediction_service dengan
pembuatan dokumen PDF menggunakan ReportLab.
"""

import tempfile
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from app.core.logger import get_logger
from app.services.prediction_service import run_prediction

logger = get_logger(__name__)


def generate_prediction_pdf(
    provinsi: str,
    jenis_cabai: str,
    durasi: int,
) -> str:
    """
    Buat file PDF laporan prediksi dan kembalikan path-nya.

    Args:
        provinsi: Nama provinsi.
        jenis_cabai: Jenis cabai.
        durasi: Jumlah hari prediksi.

    Returns:
        str: Path absolut ke file PDF yang dibuat (file sementara).

    Raises:
        InvalidInputException: Jika input tidak valid.
        InsufficientDataException: Jika data tidak cukup.
        MLModelException: Jika prediksi gagal.
    """
    logger.info(
        "Generate PDF: %s / %s | %d hari", provinsi, jenis_cabai, durasi
    )

    # Dapatkan hasil prediksi dari service
    hasil = run_prediction(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        durasi=durasi,
    )

    # Buat file PDF sementara
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp.name
    temp.close()

    _build_pdf(pdf_path, hasil)

    logger.info("PDF berhasil dibuat: %s", pdf_path)
    return pdf_path


def _build_pdf(pdf_path: str, hasil: dict) -> None:
    """
    Bangun dokumen PDF dari hasil prediksi.

    Args:
        pdf_path: Path output file PDF.
        hasil: Dict hasil prediksi dari prediction_service.
    """
    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("HASIL PREDIKSI HARGA CABAI", styles["Heading1"]))
    elements.append(
        Paragraph(f"Provinsi : {hasil['provinsi']}", styles["Normal"])
    )
    elements.append(
        Paragraph(f"Jenis Cabai : {hasil['jenis_cabai']}", styles["Normal"])
    )
    elements.append(
        Paragraph(f"Durasi : {hasil['durasi']} Hari", styles["Normal"])
    )
    elements.append(
        Paragraph(
            f"Dibuat pada : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Normal"],
        )
    )

    # Tabel prediksi
    tabel_data = [["Tanggal", "Harga Prediksi"]]
    for item in hasil["data"]:
        tabel_data.append([
            item["tanggal"],
            f"Rp {item['harga']:,}".replace(",", "."),
        ])

    table = Table(tabel_data)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#346739")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#B0BEC5")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    )

    elements.append(table)
    doc.build(elements)
