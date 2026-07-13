@echo off
echo [*] Memulai otomatisasi training LSTM & MLflow mingguan...
cd /d "C:\Users\Hanifah Az-Zahra\AndroidStudioProjects\backend"
docker compose run --rm --entrypoint /usr/local/bin/python backend train_mlflow.py
echo [✓] Otomatisasi training mingguan selesai!
