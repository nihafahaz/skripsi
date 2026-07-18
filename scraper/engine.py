"""
Engine — manajemen browser Selenium untuk scraping BI PIHPS.

Bertanggung jawab:
- Konfigurasi Chrome headless
- Membuka halaman target
- Mengklik komoditas dan tombol laporan
- Menyerahkan page_source ke parser
"""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from app.core.config import get_settings
from app.core.exceptions import ScraperException
from app.core.logger import get_logger
from app.utils.constants import JENIS_CABAI_LIST
from scraper.parser import parse_page

logger = get_logger(__name__)

# Delay (detik) untuk render halaman setelah navigasi / klik
_INITIAL_RENDER_DELAY: int = 15
_CLICK_RENDER_DELAY: int = 15
_COMMODITY_CLICK_DELAY: int = 2


def _build_chrome_options() -> Options:
    """
    Buat konfigurasi Chrome headless untuk lingkungan server/container.

    Returns:
        Options: Konfigurasi Chrome headless yang sudah siap.
    """
    settings = get_settings()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-gpu-sandbox")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--crash-dumps-dir=/tmp")
    options.binary_location = settings.chrome_bin
    return options


def run_live_scraping() -> list[dict]:
    """
    Jalankan scraping langsung dari website BI PIHPS menggunakan Selenium.

    Mengiterasi setiap jenis cabai, mengklik elemen komoditas,
    menunggu render, lalu mem-parse halaman hasil.

    Returns:
        List dict record harga yang berhasil diekstrak.

    Raises:
        ScraperException: Jika driver tidak dapat diinisialisasi.
    """
    settings = get_settings()
    options = _build_chrome_options()
    records: list[dict] = []

    try:
        service = webdriver.chrome.service.Service(settings.chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as exc:
        raise ScraperException(
            message="Gagal menginisialisasi Chrome WebDriver.",
            detail=str(exc),
        ) from exc

    try:
        logger.info("Membuka halaman: %s", settings.scraper_target_url)
        driver.get(settings.scraper_target_url)

        logger.info("Menunggu render awal (%d detik)...", _INITIAL_RENDER_DELAY)
        time.sleep(_INITIAL_RENDER_DELAY)

        for jenis in JENIS_CABAI_LIST:
            logger.info("Memproses komoditas: %s", jenis)

            try:
                element = driver.find_element(
                    By.XPATH, f"//*[normalize-space()='{jenis}']"
                )
                element.click()
                time.sleep(_COMMODITY_CLICK_DELAY)
            except Exception as exc:
                logger.warning("Gagal mengklik komoditas %s: %s", jenis, exc)
                continue

            try:
                btn_report = driver.find_element(By.ID, "btnReport")
                btn_report.click()
                logger.debug("Mengklik btnReport, menunggu render...")
                time.sleep(_CLICK_RENDER_DELAY)
            except Exception as exc:
                logger.warning(
                    "Gagal memperbarui laporan untuk %s: %s", jenis, exc
                )
                continue

            jenis_records = parse_page(driver.page_source, jenis)
            records.extend(jenis_records)
            logger.info(
                "Selesai %s: %d record.", jenis, len(jenis_records)
            )

    finally:
        driver.quit()
        logger.info("WebDriver ditutup.")

    return records
