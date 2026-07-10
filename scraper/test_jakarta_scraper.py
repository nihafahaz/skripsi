from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

o = Options()
o.add_argument('--headless=new')
o.add_argument('--no-sandbox')
o.add_argument('--disable-dev-shm-usage')
o.add_argument('--disable-gpu')
o.add_argument('--disable-gpu-sandbox')
o.add_argument('--remote-debugging-pipe')
o.binary_location = '/usr/bin/chromium'

s = Service('/usr/bin/chromedriver')

try:
    driver = webdriver.Chrome(service=s, options=o)
    url = "https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas"
    driver.get(url)
    time.sleep(15)
    
    # 1. Klik Cabai Merah Besar
    print("Klik Cabai Merah Besar...")
    el = driver.find_element(By.XPATH, "//*[normalize-space()='Cabai Merah Besar']")
    el.click()
    time.sleep(2)
    
    # 2. Klik Cabai Rawit Merah
    print("Klik Cabai Rawit Merah...")
    el = driver.find_element(By.XPATH, "//*[normalize-space()='Cabai Rawit Merah']")
    el.click()
    time.sleep(2)
    
    btn_report = driver.find_element(By.ID, "btnReport")
    btn_report.click()
    time.sleep(15)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    
    rows = soup.find_all("tr")
    
    # Cari header tanggal
    dates = []
    for row in rows:
        cols = [td.text.strip() for td in row.find_all(["td", "th"])]
        if len(cols) >= 5 and any("Komoditas" in c for c in cols[:2]):
            dates = cols[2:]
            print("Tanggal Kolom di Website:", dates)
            break
            
    for row in rows:
        cols = [td.text.strip() for td in row.find_all(["td", "th"])]
        if len(cols) >= 3 and "DKI" in cols[1].upper():
            print(f"\nDKI Jakarta Row Found:")
            print("Raw columns:", cols)
            
except Exception as e:
    print("Error:", e)
