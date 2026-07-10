import os
import pandas as pd
from database import get_db_connection
from preprocessing import interpolasi_missing_value, bersihkan_harga

try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, tanggal, harga
        FROM data_harga_clean
        WHERE provinsi='DKI Jakarta' AND jenis_cabai='Cabai Rawit Merah'
        ORDER BY tanggal ASC
    """)
    rows = cursor.fetchall()
    print(f"Jumlah baris di DB: {len(rows)}")
    
    data = pd.DataFrame(rows)
    print("\n--- 5 Baris Terakhir dari DB (Mentah) ---")
    print(data.tail(5))
    
    data["harga_clean"] = data["harga"].apply(bersihkan_harga)
    print("\n--- 5 Baris Terakhir setelah bersihkan_harga ---")
    print(data[["id", "tanggal", "harga_clean"]].tail(5))
    
    # Simulasikan interpolasi
    data_interpolated = data.copy()
    data_interpolated["harga"] = data_interpolated["harga_clean"]
    data_interpolated = interpolasi_missing_value(data_interpolated, 'DKI Jakarta', 'Cabai Rawit Merah')
    print("\n--- 5 Baris Terakhir setelah interpolasi ---")
    print(data_interpolated[["id", "tanggal", "harga"]].tail(5))
    
    # Simulasikan pembulatan
    data_interpolated["harga_rounded"] = (data_interpolated["harga"] / 100).round() * 100
    print("\n--- 5 Baris Terakhir setelah pembulatan ---")
    print(data_interpolated[["id", "tanggal", "harga_rounded"]].tail(5))
    
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
