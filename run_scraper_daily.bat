@echo off
echo [*] Memulai otomatisasi scraping harian...
cd /d "C:\Users\Hanifah Az-Zahra\AndroidStudioProjects\backend"
docker compose run --rm scraper
docker compose run --rm --entrypoint /usr/local/bin/python backend preprocessing.py
echo [✓] Otomatisasi scraping harian selesai!
