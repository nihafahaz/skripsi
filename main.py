"""
Entry point aplikasi FastAPI — backend prediksi harga cabai.

File ini hanya berisi inisialisasi minimal.
Seluruh konfigurasi dan logika ada di modul app/.

Cara menjalankan:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from app import create_app

app = create_app()