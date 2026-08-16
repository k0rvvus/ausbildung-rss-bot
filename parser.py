import os
import requests
import base64
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
}

def parse_arbeitsagentur():
    api_url = "https://arbeitsagentur.de"
    params = {"was": "Fachinformatiker/in", "wo": "09111 Chemnitz, Sachsen", "umkreis": "25", "suchbereich": "ausbildung", "page": "1", "size": "20"}
    headers = {"User-Agent": HEADERS["User-Agent"], "X-API-Key": "jobboerse-client-production-pc"}
    vacancies = []
    try:
        res = requests.get(api_url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            for job in res.json().get("stellenangebote", []):
                try:
                    title = job.get("titel", "Ausbildung")
                    company = job.get("arbeitgeber", "Не указана")
                    encoded_id = base64.b64encode(job.get("refnr").encode('utf-8')).decode('utf-8').replace('=', '')
                    link = f"https://arbeitsagentur.de{encoded_id}"
                    vacancies.append({"title": f"💼 [Arbeitsagentur] {title}", "link": link, "company": company})
                except: continue
    except: pass
    return vacancies

def parse_azubi_de():
    url = "https://azubi.de"
    vacancies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        for link_tag in soup.find_all('a', href=lambda h: h and h.startswith('/ausbildungsplatz/')):
            try:
                link = "https://azubi.de" + link_tag['href']
                title_el = link_tag.find('h2', class_=lambda c: c and 'hidden @lg:block' in c) or link_tag.find('h2')
                if not title_el: continue
                company_div = link_tag.find('div', class_='flex flex-wrap items-center gap-xs')
                company = company_div.get_text(strip=True) if company_div else "Не указана"
                vacancies.append({"title": f"⚡ [Azubi.de] {title_el.get_text(strip=True)}", "link": link, "company": company})
            except: continue
    except: pass
    return vacancies

def parse_aubi_plus():
    url = "https://aubi-plus.de"
    vacancies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        for link_tag in soup.find_all('a', class_='stretched-link'):
            try:
                link = link_tag['href']
                if not link.startswith('http'): link = "https://aubi-plus.de" + link
                card_row = link_tag.find_parent('div', class_='row')
                company = "Не указана"
                if card_row and card_row.find('img') and 'alt' in card_row.find('img').attrs:
                    company = card_row.find('img')['alt'].replace('Logo', '').strip()
                vacancies.append({"title": f"🎯 [Aubi-Plus] {link_tag.get_text(strip=True)}", "link": link, "company": company})
            except: continue
    except: pass
    return vacancies

def send_to_telegram(text):
    """Функция отправки сообщения через вашего бота"""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Ошибка: Секреты Telegram не настроены в GitHub!")
        return
        
    url = f"https://telegram.org{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}")

if __name__ == "__main__":
    print("Сбор вакансий...")
    all_jobs = parse_arbeitsagentur() + parse_azubi_de() + parse_aubi_plus()
    
    # Файл-память, чтобы бот присылал только НОВЫЕ вакансии и не спамил старыми
    sent_jobs_file = "sent_jobs.txt"
    if os.path.exists(sent_jobs_file):
        with open(sent_jobs_file, "r") as f:
            sent_links = set(f.read().splitlines())
    else:
        sent_links = set()

    new_links = []
    for job in all_jobs:
        if job['link'] not in sent_links:
            # Формируем красивый текст сообщения
            message = f"<b>{job['title']}</b>\n\n🏢 Компания: {job['company']}\n🔗 Ссылка: {job['link']}"
            send_to_telegram(message)
            new_links.append(job['link'])
            print(f"Отправлено в ТГ: {job['title']}")

    # Запоминаем отправленные ссылки
    if new_links:
        with open(sent_jobs_file, "a") as f:
            for link in new_links:
                f.write(link + "\n")
