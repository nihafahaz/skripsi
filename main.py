from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db_connection
import os
import joblib
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

app = FastAPI()
LAG = 1
MODEL_CUTOFF_DATE = "2026-06-21"

PROVINSI_LIST = sorted([
    'Aceh', 'Bali', 'Banten', 'Bengkulu', 'DI Yogyakarta', 'DKI Jakarta',
    'Gorontalo', 'Jambi', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur',
    'Kalimantan Barat', 'Kalimantan Selatan', 'Kalimantan Tengah',
    'Kalimantan Timur', 'Kalimantan Utara', 'Kepulauan Bangka Belitung',
    'Kepulauan Riau', 'Lampung', 'Maluku', 'Maluku Utara',
    'Nusa Tenggara Barat', 'Nusa Tenggara Timur', 'Papua', 'Papua Barat',
    'Riau', 'Sulawesi Barat', 'Sulawesi Selatan', 'Sulawesi Tengah',
    'Sulawesi Tenggara', 'Sulawesi Utara', 'Sumatera Barat',
    'Sumatera Selatan', 'Sumatera Utara'
])

JENIS_CABAI_LIST = sorted([
    'Cabai Merah Besar',
    'Cabai Merah Keriting',
    'Cabai Rawit Merah',
    'Cabai Rawit Hijau'
])

class PredictRequest(BaseModel):
    provinsi: str
    jenis_cabai: str
    durasi: int

@app.get("/")
def home():
    return {
        "message" : "Backend Prediksi Harga Cabai Aktif"
    }

@app.get("/harga")
def harga(
    provinsi: str | None = None,
    jenis_cabai: str | None = None,
    limit: int = Query(default=10, le=100)
):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = "SELECT * FROM data_harga_clean WHERE 1=1"
        params = []

        if provinsi:
            query += " AND provinsi = %s"
            params.append(provinsi)

        if jenis_cabai:
            query += " AND jenis_cabai = %s"
            params.append(jenis_cabai)

        query += " ORDER BY tanggal DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        result = cursor.fetchall()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "jumlah_data": len(result),
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
def buat_model_lstm():
    model = Sequential()
    model.add(LSTM(32, input_shape=(1, 39)))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(loss="mse", optimizer="adam")
    return model

def load_model_dan_scaler():
    weights_path = "models/global_lstm.weights.h5"
    scaler_path = "scalers/global_scaler.save"

    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Weights tidak ditemukan: {weights_path}")

    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler tidak ditemukan: {scaler_path}")

    model = buat_model_lstm()
    model.load_weights(weights_path)

    scaler = joblib.load(scaler_path)

    return model, scaler

def proses_prediksi(request: PredictRequest):
    try:
        if request.provinsi not in PROVINSI_LIST or request.jenis_cabai not in JENIS_CABAI_LIST:
            return {
                "status": "error",
                "message": f"Provinsi atau Jenis Cabai tidak terdaftar."
            }

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT tanggal, harga
            FROM data_harga_clean
            WHERE provinsi = %s 
            AND jenis_cabai = %s
            AND tanggal <= %s
            ORDER BY tanggal DESC
            LIMIT %s
        """

        cursor.execute(query, (request.provinsi, request.jenis_cabai, MODEL_CUTOFF_DATE, LAG))
        data_historis = cursor.fetchall()

        if len(data_historis) < LAG:
            return {
                "status": "error",
                "message": f"Data historis kurang. Butuh minimal {LAG} data."
            }

        model, scaler = load_model_dan_scaler()

        data_historis = list(reversed(data_historis))

        tanggal_terakhir = data_historis[-1]["tanggal"]
        harga_terakhir = data_historis[-1]["harga"]

        harga_sequence = np.array([
            float(item["harga"]) for item in data_historis
        ]).reshape(-1, 1)

        scaled_sequence = scaler.transform(harga_sequence)

        # OHE Mapping
        prov_idx = PROVINSI_LIST.index(request.provinsi)
        chili_idx = JENIS_CABAI_LIST.index(request.jenis_cabai)

        prov_ohe = np.zeros(len(PROVINSI_LIST))
        prov_ohe[prov_idx] = 1.0

        chili_ohe = np.zeros(len(JENIS_CABAI_LIST))
        chili_ohe[chili_idx] = 1.0

        ohe_features = np.concatenate([prov_ohe, chili_ohe])

        # Bentuk initial feature vector size (1, 1, 39)
        current_seq_features = np.zeros((1, 1, 39))
        current_seq_features[0, 0, 0] = scaled_sequence[0][0]
        current_seq_features[0, 0, 1:] = ohe_features

        hasil_prediksi = []

        for i in range(request.durasi):
            pred_scaled = model.predict(current_seq_features, verbose=0)

            pred_harga = scaler.inverse_transform(pred_scaled)[0][0]
            pred_harga = int(round(pred_harga))

            tanggal_prediksi = tanggal_terakhir + timedelta(days=i + 1)

            hasil_prediksi.append({
                "tanggal": tanggal_prediksi.strftime("%Y-%m-%d"),
                "harga": pred_harga
            })

            # Update feature vector untuk prediksi hari berikutnya
            next_seq_features = np.zeros((1, 1, 39))
            next_seq_features[0, 0, 0] = pred_scaled[0][0]
            next_seq_features[0, 0, 1:] = ohe_features
            current_seq_features = next_seq_features

        tanggal_mulai = tanggal_terakhir + timedelta(days=1)
        tanggal_selesai = tanggal_terakhir + timedelta(days=request.durasi)

        query_aktual = """
        SELECT tanggal, harga
        FROM data_harga_clean
        WHERE provinsi = %s
        AND jenis_cabai = %s
        AND tanggal BETWEEN %s AND %s
        ORDER BY tanggal ASC
        """

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            query_aktual,
            (
                request.provinsi,
                request.jenis_cabai,
                tanggal_mulai,
                tanggal_selesai
            )
        )

        data_aktual = cursor.fetchall()

        cursor.close()
        connection.close()

        aktual_dict = {
            item["tanggal"].strftime("%Y-%m-%d"): item["harga"]
            for item in data_aktual
        }

        data_aktual_final = []

        for prediksi in hasil_prediksi:
            tanggal = prediksi["tanggal"]

            data_aktual_final.append({
                "tanggal": tanggal,
                "harga": aktual_dict.get(tanggal)
            })

        return {
            "status": "success",
            "provinsi": request.provinsi,
            "jenis_cabai": request.jenis_cabai,
            "durasi": request.durasi,
            "harga_terakhir": harga_terakhir,
            "tanggal_terakhir": tanggal_terakhir.strftime("%Y-%m-%d"),
            "data": hasil_prediksi,
            "data_aktual": data_aktual_final
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/predict")
def predict(request: PredictRequest):
    return proses_prediksi(request)

@app.get("/toko_online")
def toko_online():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT 
            id,
            nama_toko,
            platform,
            nama_produk,
            jenis_cabai,
            harga,
            satuan,
            lokasi,
            rating,
            link_toko,
            gambar_toko AS gambar_produk
        FROM toko_online
        """

        cursor.execute(query)
        data = cursor.fetchall()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "data": data
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/download")
def download(
    provinsi: str,
    jenis_cabai: str,
    durasi: int,
):
    
    request = PredictRequest(
    provinsi=provinsi,
    jenis_cabai=jenis_cabai,
    durasi=durasi,
    )

    hasil = proses_prediksi(request)

    if hasil["status"] == "error":
        return hasil
    
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp.name
    temp.close()

    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("HASIL PREDIKSI HARGA CABAI", styles["Heading1"]))
    elements.append(Paragraph(f"Provinsi : {hasil['provinsi']}", styles["Normal"]))
    elements.append(Paragraph(f"Jenis Cabai : {hasil['jenis_cabai']}", styles["Normal"]))
    elements.append(Paragraph(f"Durasi : {hasil['durasi']} Hari", styles["Normal"]))

    tabel_prediksi = [["Tanggal", "Harga"]]

    for item in hasil["data"]:
        tabel_prediksi.append([
            item["tanggal"],
            f"Rp {item['harga']:,}"
        ])

    table = Table(tabel_prediksi)

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.green),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),

        ("GRID",(0,0),(-1,-1),1,colors.black),

        ("ALIGN",(0,0),(-1,-1),"CENTER"),

        ("BOTTOMPADDING",(0,0),(-1,0),10),
    ]))

    elements.append(table)

    doc.build(elements)

    return FileResponse(
        pdf_path,
        filename="hasil_prediksi.pdf",
        media_type="application/pdf",
    )    