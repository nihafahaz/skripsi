"""
Parser — ekstraksi data harga dari HTML halaman BI PIHPS.

Menerima page_source HTML (string) dan mengembalikan record mentah
yang siap dibersihkan oleh cleaner.
"""

from bs4 import BeautifulSoup

from app.core.logger import get_logger
from scraper.cleaner import clean_record
from scraper.mapper import get_canonical_province_name

logger = get_logger(__name__)


def parse_dates_from_header(rows: list) -> list[str | None]:
    """
    Ekstrak daftar tanggal dari baris header tabel BI PIHPS.

    Header mengandung tanggal dalam format DD/MM/YYYY di kolom ke-3 dst.

    Args:
        rows: List BeautifulSoup <tr> element dari tabel.

    Returns:
        List tanggal dalam format YYYY-MM-DD (None jika gagal parse).
    """
    for row in rows:
        cols = [td.text.strip() for td in row.find_all(["td", "th"])]
        if len(cols) >= 5 and any("Komoditas" in c for c in cols[:2]):
            dates: list[str | None] = []
            for col_val in cols[2:]:
                clean_str = col_val.replace(" ", "")
                try:
                    d, m, y = clean_str.split("/")
                    dates.append(f"{y}-{m}-{d}")
                except Exception:
                    dates.append(None)
            logger.debug("Tanggal kolom ditemukan: %s", dates)
            return dates
    return []


def parse_price_rows(
    rows: list,
    dates: list[str | None],
    jenis_cabai: str,
) -> list[dict]:
    """
    Ekstrak record harga dari baris-baris data tabel BI PIHPS.

    Args:
        rows: List BeautifulSoup <tr> element.
        dates: List tanggal kolom (output parse_dates_from_header).
        jenis_cabai: Nama jenis cabai yang sedang diproses.

    Returns:
        List dict record harga yang valid (sudah divalidasi cleaner).
    """
    records: list[dict] = []

    for row in rows:
        cols = [td.text.strip() for td in row.find_all(["td", "th"])]
        if len(cols) < 3:
            continue

        raw_prov = cols[1].upper().strip()
        canonical_prov = get_canonical_province_name(raw_prov)

        if canonical_prov is None:
            continue

        for idx, price_raw in enumerate(cols[2:]):
            if idx >= len(dates) or dates[idx] is None:
                continue

            record = clean_record(
                tanggal=dates[idx],
                provinsi=canonical_prov,
                jenis_cabai=jenis_cabai,
                harga_raw=price_raw,
            )
            if record is not None:
                records.append(record)

    return records


def parse_page(page_source: str, jenis_cabai: str) -> list[dict]:
    """
    Parse seluruh page source HTML untuk satu jenis cabai.

    Args:
        page_source: HTML string dari driver.page_source.
        jenis_cabai: Nama jenis cabai yang sedang diproses.

    Returns:
        List dict record harga yang valid.
    """
    soup = BeautifulSoup(page_source, "html.parser")
    rows = soup.find_all("tr")

    dates = parse_dates_from_header(rows)
    if not dates:
        logger.warning(
            "Header tanggal tidak ditemukan untuk jenis cabai: %s", jenis_cabai
        )
        return []

    records = parse_price_rows(rows, dates, jenis_cabai)
    logger.info(
        "Berhasil mengekstrak %d record untuk %s.", len(records), jenis_cabai
    )
    return records
