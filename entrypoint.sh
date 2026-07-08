#!/bin/sh

# Tunggu sampai MySQL siap
echo "Waiting for MySQL database on ${DB_HOST:-mysql}:3306..."
while ! nc -z ${DB_HOST:-mysql} 3306; do
  sleep 1
done
echo "MySQL is up and running!"

# Cek apakah tabel data_harga_clean kosong
TABLE_COUNT=$(python -c "
import os, pymysql
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', 'mysql'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'db_cabai')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM data_harga_clean')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except Exception as e:
    print(0)
")

if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "Database is empty. Running database seeding..."
    python import_clean_to_mysql.py
    python import_toko.py
    echo "Database seeding completed."
else
    echo "Database already seeded (contains $TABLE_COUNT records). Skipping seed."
fi

# Jalankan FastAPI server
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
