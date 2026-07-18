#!/bin/sh

# Tunggu sampai MySQL siap
echo "Waiting for MySQL on ${DB_HOST}:${DB_PORT:-3306}..."
while ! nc -z ${DB_HOST} ${DB_PORT:-3306}; do
  sleep 1
done
echo "MySQL is up!"

# Cek apakah tabel data_harga_clean kosong
TABLE_COUNT=$(python -c "
import os, pymysql
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'db_cabai')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM data_harga_clean')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except Exception:
    print(0)
")

if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "Database kosong. Menjalankan seeding pipeline..."

    echo "[1/3] Seeding toko online..."
    python scripts/seed_stores.py

    echo "[2/3] Generating data sintetis untuk kombinasi kosong..."
    python scripts/synthesize_data.py

    echo "Seeding selesai."
else
    echo "Database sudah terisi ($TABLE_COUNT records). Skip seeding."
fi

# Jalankan FastAPI server
echo "Menjalankan FastAPI server..."
exec "$@"
