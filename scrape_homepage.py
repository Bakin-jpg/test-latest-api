# scrape_homepage.py
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

BASE_URL = "https://aniwatchtv.to"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Referer': 'https://aniwatchtv.to/'
}

def setup_selenium_driver():
    """Menyiapkan driver Selenium Chrome dengan mode stealth."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    return driver

def get_soup(url):
    """Hanya menggunakan requests untuk halaman utama yang statis."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error (requests): {e}"); return None

# --- [FUNGSI KUNCI BARU DENGAN SELENIUM] ---
def get_latest_episode_stream_url(driver, series_watch_url):
    """
    Menggunakan Selenium untuk membuka halaman seri, mengklik episode TERAKHIR,
    dan mendapatkan URL stream-nya.
    """
    if not series_watch_url: return None
    print(f"  -> Memproses seri: {series_watch_url}")
    try:
        driver.get(series_watch_url)
        wait = WebDriverWait(driver, 20)
        
        # 1. Tunggu hingga daftar episode dimuat
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ss-list .ssl-item.ep-item")))
        time.sleep(2) # Beri waktu ekstra agar semua elemen benar-benar render
        
        # 2. Ambil SEMUA episode, lalu pilih yang TERAKHIR
        episode_elements = driver.find_elements(By.CSS_SELECTOR, ".ss-list .ssl-item.ep-item")
        if not episode_elements:
            print("    -> Gagal: Tidak ada elemen episode ditemukan.")
            return None
            
        latest_episode_element = episode_elements[-1] # Ambil elemen terakhir dari daftar
        episode_title = latest_episode_element.get_attribute('title')
        print(f"    -> Menemukan episode terakhir: '{episode_title}'")
        
        # 3. Klik episode terakhir untuk memuat videonya
        latest_episode_element.click()
        
        # 4. Tunggu hingga iframe untuk episode ini dimuat
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe-embed")))
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        driver.switch_to.default_content() # Kembali dari iframe
        
        iframe_element = driver.find_element(By.ID, "iframe-embed")
        stream_src = iframe_element.get_attribute('src')
        
        if stream_src and ('megacloud' in stream_src or 'vidstream' in stream_src):
            final_stream_url = f"{stream_src}&autoPlay=1&oa=0&asi=1"
            print(f"    -> Ditemukan URL Stream: {final_stream_url[:70]}...")
            return final_stream_url
        
        print("    -> Gagal: Atribut src iframe kosong setelah diklik.")
        return None

    except Exception as e:
        print(f"    -> Gagal memproses dengan Selenium: {type(e).__name__}")
        return None

def scrape_homepage_sections(soup):
    """Mengambil data dasar dari halaman utama."""
    data = {'spotlight': [], 'latest_episodes': []}
    if not soup: return data

    for item in soup.select('#slider .deslide-item'):
        title_el = item.select_one('.desi-head-title')
        watch_now_el = item.select_one('a.btn-primary')
        img_el = item.select_one('img.film-poster-img')
        if title_el and watch_now_el and img_el:
            data['spotlight'].append({
                'title': title_el.text.strip(),
                'series_watch_url': f"{BASE_URL}{watch_now_el['href']}",
                'image_url': img_el.get('data-src'),
            })

    for item in soup.select('section.block_area_home .flw-item'):
        link_el = item.select_one('a.film-poster-ahref')
        img_el = item.select_one('img.film-poster-img')
        if link_el and link_el.has_attr('href') and img_el:
            data['latest_episodes'].append({
                'title': link_el.get('title') or link_el.get('oldtitle', 'N/A'),
                # URL ini sekarang menunjuk ke halaman seri, bukan episode spesifik
                'series_watch_url': f"{BASE_URL}{link_el['href'].replace('?ep=', '')}", 
                'image_url': img_el.get('data-src'),
            })
    return data

def main():
    print("Memulai scraper update homepage (Metode Hybrid Selenium)...")
    home_soup = get_data(f"{BASE_URL}/home")
    
    if not home_soup:
        print("Kritis: Gagal memuat halaman utama. Proses dihentikan."); return

    homepage_data = scrape_homepage_sections(home_soup)

    print("Menyiapkan driver Selenium dengan mode STEALTH...")
    driver = setup_selenium_driver()

    # Gabungkan kedua list untuk diproses dengan cara yang sama
    all_anime_to_process = homepage_data['spotlight'] + homepage_data['latest_episodes']

    print("\n--- Memproses semua anime di homepage ---")
    for anime in all_anime_to_process:
        anime['stream_url'] = get_latest_episode_stream_url(driver, anime.get('series_watch_url'))
        time.sleep(random.uniform(1, 2))
        
    driver.quit()

    with open('anime_homepage.json', 'w', encoding='utf-8') as f:
        json.dump(homepage_data, f, ensure_ascii=False, indent=2)
    print("\nData halaman utama berhasil diperbarui di 'anime_homepage.json'")

if __name__ == "__main__":
    main()
