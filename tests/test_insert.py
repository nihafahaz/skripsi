import pymysql

try:
    conn = pymysql.connect(
        host='mysql',
        user='root',
        password='',
        database='db_cabai'
    )
    cursor = conn.cursor()
    
    # Insert test row
    print("Inserting test row...")
    cursor.execute("""
        INSERT INTO data_harga_clean (tanggal, provinsi, jenis_cabai, harga)
        VALUES ('2026-12-31', 'Test Prov', 'Test Chili', 12345)
    """)
    
    # Read back
    cursor.execute("""
        SELECT harga FROM data_harga_clean
        WHERE tanggal='2026-12-31' AND provinsi='Test Prov' AND jenis_cabai='Test Chili'
    """)
    result = cursor.fetchone()
    print("Read back value:", result[0])
    
    # Clean up
    cursor.execute("""
        DELETE FROM data_harga_clean
        WHERE tanggal='2026-12-31' AND provinsi='Test Prov' AND jenis_cabai='Test Chili'
    """)
    conn.commit()
    
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
