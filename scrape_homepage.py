# scrape_homepage.py
import requests
from bs4 import BeautifulSoup
import json
import time
import random

BASE_URL = "https://aniwatchtv.to"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Referer': 'https://aniwatchtv.to/',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_data(url, is_json=False):
    """Fungsi generik untuk mengambil data, bisa HTML atau JSON."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        if is_json:
            return response.json()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"  -> Gagal mengambil data dari {url}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"  -> Gagal mem-parsing JSON dari {url}")
        return None

def get_stream_url_from_ajax(episode_id):
    """Mengambil URL stream langsung dari endpoint AJAX v2."""
    if not episode_id:
        print("    -> Gagal: Tidak ada ID episode.")
        return None
    
    ajax_url = f"{BASE_URL}/ajax/v2/episode/sources?id={episode_id}"
    print(f"  -> Memanggil API stream: {ajax_url}")
    data = get_data(ajax_url, is_json=True)
    
    if data and 'link' in data:
        base_link = data['link']
        # Menambahkan parameter autoplay sesuai temuan Anda
        final_stream_url = f"{base_link}&autoPlay=1&oa=0&asi=1"
        print(f"    -> Ditemukan: {final_stream_url[:70]}...")
        return final_stream_url
    else:
        print("    -> Gagal: Respons JSON tidak valid atau tidak berisi link.")
        return None

def get_first_episode_id(series_watch_url):
    """Mengunjungi halaman seri untuk mendapatkan ID episode pertama."""
    print(f"  -> Mencari episode pertama dari: {series_watch_url}")
    soup = get_data(series_watch_url)
    if not soup:
        return None
    
    first_ep_el = soup.select_one('.ss-list .ssl-item.ep-item')
    if first_ep_el and first_ep_el.has_attr('data-id'):
        ep_id = first_ep_el['data-id']
        print(f"    -> ID episode pertama: {ep_id}")
        return ep_id
    
    print(f"    -> Gagal menemukan daftar episode untuk {series_watch_url}")
    return None

def scrape_homepage_sections(soup):
    """Mengambil data dari halaman utama dan mengekstrak ID yang diperlukan."""
    data = {'spotlight': [], 'latest_episodes': []}
    if not soup: return data

    # Spotlight
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

    # Latest Episodes
    for item in soup.select('section.block_area_home .flw-item'):
        link_el = item.select_one('a.film-poster-ahref')
        img_el = item.select_one('img.film-poster-img')
        if link_el and link_el.has_attr('data-id') and img_el:
            data['latest_episodes'].append({
                'title': link_el.get('title') or link_el.get('oldtitle', 'N/A'),
                'episode_id': link_el['data-id'],
                'image_url': img_el.get('data-src'),
            })
    return data

def main():
    print("Memulai scraper update homepage (Metode AJAX Cepat)...")
    home_soup = get_data(f"{BASE_URL}/home")
    
    if not home_soup:
        print("Kritis: Gagal memuat halaman utama. Proses dihentikan.")
        return

    homepage_data = scrape_homepage_sections(home_soup)

    print("\n--- Memproses Spotlight ---")
    for anime in homepage_data['spotlight']:
        first_ep_id = get_first_episode_id(anime['series_watch_url'])
        anime['stream_url'] = get_stream_url_from_ajax(first_ep_id)
        time.sleep(random.uniform(0.5, 1))
    
    print("\n--- Memproses Latest Episodes ---")
    for anime in homepage_data['latest_episodes']:
        anime['stream_url'] = get_stream_url_from_ajax(anime.get('episode_id'))
        time.sleep(random.uniform(0.5, 1))
        
    with open('anime_homepage.json', 'w', encoding='utf-8') as f:
        json.dump(homepage_data, f, ensure_ascii=False, indent=2)
    print("\nData halaman utama berhasil diperbarui di 'anime_homepage.json'")

if __name__ == "__main__":
    main()
