import os
import argparse
import sys
import time
from datetime import datetime, timedelta
from database import get_db_connection
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Konfigurasi path agar bisa mengimpor main.py meskipun dijalankan dari lokasi berbeda
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import proses_prediksi, PredictRequest

def get_all_combinations():
    """Mengambil semua kombinasi unik provinsi dan jenis cabai dari database."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT DISTINCT provinsi, jenis_cabai FROM data_harga_clean"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return rows
    except Exception as e:
        print(f"[-] Gagal membaca database: {e}")
        return []

def generate_pdf_report(provinsi: str, jenis_cabai: str, durasi: int, output_dir: str):
    """Menjalankan prediksi dan membuat file PDF laporan di folder tujuan."""
    request = PredictRequest(
        provinsi=provinsi,
        jenis_cabai=jenis_cabai,
        durasi=durasi
    )
    
    # Panggil fungsi prediksi utama dari backend
    hasil = proses_prediksi(request)
    
    if hasil["status"] == "error":
        print(f"[-] Gagal memproses prediksi untuk {provinsi} - {jenis_cabai}: {hasil['message']}")
        return False
        
    # Pastikan folder output dibuat
    os.makedirs(output_dir, exist_ok=True)
    tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
    
    # Format nama file: Laporan_Jawa_Barat_Cabai_Rawit_Merah_2026-07-08.pdf
    nama_file = f"Laporan_{provinsi.replace(' ', '_')}_{jenis_cabai.replace(' ', '_')}_{tanggal_hari_ini}.pdf"
    pdf_path = os.path.join(output_dir, nama_file)
    
    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    elements = []
    
    # Judul Laporan
    elements.append(Paragraph("LAPORAN PREDIKSI HARGA CABAI", styles["Heading1"]))
    elements.append(Paragraph(f"<b>Provinsi:</b> {provinsi}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Jenis Cabai:</b> {jenis_cabai}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Durasi Prediksi:</b> {durasi} Hari", styles["Normal"]))
    elements.append(Paragraph(f"<b>Tanggal Generate:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    
    # Penyusunan Tabel Data
    tabel_prediksi = [["Tanggal", "Prediksi Harga", "Harga Aktual"]]
    
    data_pred = hasil["data"]
    data_akt = hasil.get("data_aktual", [])
    
    # Buat dictionary untuk pencarian harga aktual yang cepat berdasarkan tanggal
    aktual_dict = {item["tanggal"]: item["harga"] for item in data_akt}
    
    for item in data_pred:
        tgl = item["tanggal"]
        harga_pred = f"Rp {item['harga']:,}".replace(",", ".")
        
        harga_akt_raw = aktual_dict.get(tgl)
        harga_akt = f"Rp {harga_akt_raw:,}".replace(",", ".") if harga_akt_raw is not None else "-"
        
        tabel_prediksi.append([tgl, harga_pred, harga_akt])
        
    table = Table(tabel_prediksi)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#346739")), # Menggunakan AppColors.primary
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#B0BEC5")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    
    elements.append(table)
    
    try:
        doc.build(elements)
        print(f"[+] Berhasil menyimpan laporan: {pdf_path}")
        return True
    except Exception as e:
        print(f"[-] Gagal membangun PDF untuk {provinsi} - {jenis_cabai}: {str(e)}")
        return False

def run_all(durasi: int, output_dir: str, target_provinsi=None, target_cabai=None):
    """Menjalankan proses pembuatan PDF untuk seluruh kombinasi yang valid."""
    print("[*] Memulai generate laporan otomatis...")
    combinations = get_all_combinations()
    if not combinations:
        print("[-] Tidak ada kombinasi provinsi dan jenis cabai yang ditemukan.")
        return
        
    sukses = 0
    gagal = 0
    lewat = 0
    
    for provinsi, jenis_cabai in combinations:
        # Filter jika parameter spesifik ditentukan
        if target_provinsi and provinsi.lower() != target_provinsi.lower():
            continue
        if target_cabai and jenis_cabai.lower() != target_cabai.lower():
            continue
            
        # Cek keberadaan model LSTM dan Scaler sebelum melakukan prediksi
        nama_file = f"{provinsi}_{jenis_cabai}"
        weights_path = f"models/{nama_file}.weights.h5"
        scaler_path = f"scalers/{nama_file}_scaler.save"
        
        if not os.path.exists(weights_path) or not os.path.exists(scaler_path):
            print(f"[!] Model/scaler untuk {provinsi} - {jenis_cabai} belum dilatih. Melewati...")
            lewat += 1
            continue
            
        print(f"[*] Memproses {provinsi} ({jenis_cabai})...")
        if generate_pdf_report(provinsi, jenis_cabai, durasi, output_dir):
            sukses += 1
        else:
            gagal += 1
            
    print(f"\n======================================")
    print(f"Proses Pembuatan Laporan Selesai:")
    print(f"- Sukses: {sukses}")
    print(f"- Gagal: {gagal}")
    print(f"- Dilewati (Model belum ada): {lewat}")
    print(f"======================================\n")

def start_scheduler(hour: int, minute: int, durasi: int, output_dir: str):
    """Menjalankan scheduler loop tanpa menggunakan dependency eksternal."""
    print(f"[*] Scheduler Aktif. Laporan akan otomatis dibuat setiap hari pukul {hour:02d}:{minute:02d}")
    while True:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Jika waktu target sudah lewat hari ini, jadwalkan besok
        if target <= now:
            target += timedelta(days=1)
            
        delay_seconds = (target - now).total_seconds()
        print(f"[*] Menunggu {delay_seconds:.1f} detik hingga {target.strftime('%Y-%m-%d %H:%M:%S')}...")
        
        time.sleep(delay_seconds)
        
        print(f"\n[*] Waktu target tercapai. Memulai tugas otomatis harian...")
        run_all(durasi, output_dir)
        print("[*] Tugas selesai. Kembali menjadwalkan untuk hari berikutnya.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script Otomatisasi Generate Laporan PDF Prediksi Cabai")
    
    parser.add_argument("--once", action="store_true", help="Jalankan generate laporan sekali saja lalu keluar (Cocok untuk Task Scheduler / Cron)")
    parser.add_argument("--scheduler", action="store_true", help="Jalankan scheduler background loop")
    parser.add_argument("--time", type=str, default="08:00", help="Waktu generate laporan pada mode scheduler (format HH:MM, default 08:00)")
    parser.add_argument("--durasi", type=int, default=7, help="Durasi prediksi dalam hari (default: 7)")
    parser.add_argument("--outdir", type=str, default="./laporan_pdf", help="Direktori penyimpanan file PDF hasil generate (default: ./laporan_pdf)")
    parser.add_argument("--provinsi", type=str, default=None, help="Filter spesifik provinsi")
    parser.add_argument("--cabai", type=str, default=None, help="Filter spesifik jenis cabai")
    
    args = parser.parse_args()
    
    if args.scheduler:
        try:
            h, m = map(int, args.time.split(":"))
            start_scheduler(h, m, args.durasi, args.outdir)
        except ValueError:
            print("[-] Format parameter --time salah. Gunakan format HH:MM (contoh: 08:30)")
    else:
        # Secara default, jalankan sekali
        run_all(args.durasi, args.outdir, args.provinsi, args.cabai)
