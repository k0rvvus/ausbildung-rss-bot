import os
import requests
import base64
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# Общие заголовки для имитации браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
}

def parse_arbeitsagentur():
    """1. Сбор с Федеральной биржи труда (Arbeitsagentur.de) через API"""
    api_url = "https://arbeitsagentur.de"
    params = {
        "was": "Fachinformatiker/in",
        "wo": "09111 Chemnitz, Sachsen",
        "umkreis": "25",
        "suchbereich": "ausbildung",
        "page": "1",
        "size": "20"
    }
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "X-API-Key": "jobboerse-client-production-pc"
    }
    vacancies = []
    try:
        res = requests.get(api_url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            job_list = res.json().get("stellenangebote", [])
            for job in job_list:
                try:
                    title = job.get("titel", "Ausbildung")
                    company = job.get("arbeitgeber", "Не указана")
                    ref_id = job.get("refnr")
                    encoded_id = base64.b64encode(ref_id.encode('utf-8')).decode('utf-8').replace('=', '')
                    link = f"https://arbeitsagentur.de{encoded_id}"
                    
                    vacancies.append({
                        "title": f"[Arbeitsagentur] {title}",
                        "link": link,
                        "description": f"Компания: {company}\nИсточник: Arbeitsagentur.de"
                    })
                except: continue
    except Exception as e:
        print(f"Ошибка Arbeitsagentur: {e}")
    return vacancies

def parse_azubi_de():
    """2. Сбор с сайта Azubi.de на основе вашего HTML-кода"""
    url = "https://azubi.de"
    vacancies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        
        job_links = soup.find_all('a', href=lambda h: h and h.startswith('/ausbildungsplatz/'))
        
        for link_tag in job_links:
            try:
                link = "https://azubi.de" + link_tag['href']
                title_el = link_tag.find('h2', class_=lambda c: c and 'hidden @lg:block' in c) or link_tag.find('h2')
                if not title_el: continue
                title = title_el.get_text(strip=True)
                
                company_div = link_tag.find('div', class_='flex flex-wrap items-center gap-xs')
                company = company_div.get_text(strip=True) if company_div else "Не указана"
                
                vacancies.append({
                    "title": f"[Azubi.de] {title}",
                    "link": link,
                    "description": f"Компания: {company}\nИсточник: Azubi.de"
                })
            except: continue
    except Exception as e:
        print(f"Ошибка Azubi.de: {e}")
    return vacancies

def parse_aubi_plus():
    """3. Сбор с сайта Aubi-Plus.de на основе вашего HTML-кода"""
    url = "https://www.aubi-plus.de/suchmaschine/suche/?aSuggestLat=&aSuggestLon=&bAZA=&bAZF=&bAZS=&bAZU=&mSuggest=Fachinformatiker%2Fin&aSuggest=09111&submit=Suchen"
    vacancies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Находим ссылки со специальным классом stretched-link, который вы прислали в логе
        job_links = soup.find_all('a', class_='stretched-link')
        
        for link_tag in job_links:
            try:
                link = link_tag['href']
                if not link.startswith('http'):
                    link = "https://www.aubi-plus.de" + link
                
                title = link_tag.get_text(strip=True)
                
                # Ищем логотип компании, чтобы достать название из атрибута alt
                card_row = link_tag.find_parent('div', class_='row')
                company = "Не указана"
                if card_row:
                    img_tag = card_row.find('img')
                    if img_tag and 'alt' in img_tag.attrs:
                        company = img_tag['alt'].replace('Logo', '').strip()
                
                vacancies.append({
                    "title": f"[Aubi-Plus] {title}",
                    "link": link,
                    "description": f"Компания: {company}\nИсточник: Aubi-Plus.de"
                })
            except: continue
    except Exception as e:
        print(f"Ошибка Aubi-Plus: {e}")
    return vacancies

def parse_ausbildung_de():
    """4. Сбор с сайта Ausbildung.de"""
    url = "https://ausbildung.de"
    vacancies = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        
        job_links = soup.find_all('a', href=lambda h: h and h.startswith('/stellen/'))
        
        for link_tag in job_links:
            try:
                link = "https://ausbildung.de" + link_tag['href']
                title_el = link_tag.find('h3') or link_tag.find('h2')
                if not title_el: continue
                title = title_el.get_text(strip=True)
                
                vacancies.append({
                    "title": f"[Ausbildung.de] {title}",
                    "link": link,
                    "description": f"Свежая вакансия в Хемнице.\nИсточник: Ausbildung.de"
                })
            except: continue
    except Exception as e:
        print(f"Ошибка Ausbildung.de: {e}")
    return vacancies

def generate_rss(all_vacancies):
    fg = FeedGenerator()
    fg.title('Супер-Агрегатор Ausbildung: Chemnitz IT')
    fg.link(href='https://github.com', rel='alternate')
    fg.description('Общий RSS-фид вакансий Fachinformatiker в Хемнице с 4-х сайтов')
    
    if not all_vacancies:
        fe = fg.add_entry()
        fe.title("Новых вакансий пока нет")
        fe.link(href="https://github.com")
        fe.description("Проверка завершена. На сайтах нет новых мест.")
        fe.id("empty_stub")
    else:
        for job in all_vacancies:
            fe = fg.add_entry()
            fe.title(job['title'])
            fe.link(href=job['link'])
            fe.description(job['description'])
            fe.id(job['link']) # Защита от дублей в Telegram
            
    fg.rss_file('feed.xml', pretty=True)
    print("Итоговый файл feed.xml успешно перезаписан со всех сайтов!")

if __name__ == "__main__":
    print("Запуск мега-парсинга сайтов...")
    list_1 = parse_arbeitsagentur()
    list_2 = parse_azubi_de()
    list_3 = parse_aubi_plus()
    list_4 = parse_ausbildung_de()
    
    total_jobs = list_1 + list_2 + list_3 + list_4
    
    # Склеиваем и чистим дубликаты
    unique_jobs = {v['link']: v for v in total_jobs}.values()
    
    print(f"Собрано: Arbeitsagentur ({len(list_1)}), Azubi.de ({len(list_2)}), Aubi-Plus ({len(list_3)}), Ausbildung.de ({len(list_4)})")
    generate_rss(list(unique_jobs))
