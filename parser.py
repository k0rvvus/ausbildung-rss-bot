import os
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


def clean_text(text):
    """Схлопывает пробелы/переносы, которые остаются после get_text()."""
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------------------
# 1. arbeitsagentur.de
# ---------------------------------------------------------------------------
def parse_arbeitsagentur():
    url = "https://www.arbeitsagentur.de/jobsuche/suche"
    params = {
        "suchbereich": "ausbildung",
        "was": "Fachinformatiker/in",
        "wo": "09111 Chemnitz, Sachsen",
        "umkreis": "25",
    }
    vacancies = []
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=20)
        print(f"[arbeitsagentur] status={res.status_code}, len={len(res.text)}")
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        seen = set()
        # каждая вакансия — <article class="ergebnisliste-item">
        for article in soup.find_all("article", class_="ergebnisliste-item"):
            a = article.find("a", href=re.compile(r"/jobsuche/jobdetail/"))
            if not a:
                continue
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.arbeitsagentur.de" + link
            if link in seen:
                continue
            seen.add(link)

            titel_div = article.find("div", class_="titel-lane")
            firma_div = article.find("div", class_="firma-lane")

            title = clean_text(titel_div.get_text()) if titel_div else clean_text(a.get_text())
            title = re.sub(r"^\d+\.\s*", "", title)  # убираем "1. " в начале
            company = clean_text(firma_div.get_text()) if firma_div else "Не указана"

            # доп. поля: место, дата начала, зарплата — уже есть в том же ответе
            ort_span = article.find("span", id=re.compile(r"eintrag-\d+-arbeitsort"))
            date_li = article.find("li", class_="eintrittsdatum-tag")
            gehalt_li = article.find("li", class_="gehalt-tag")

            location = clean_text(ort_span.get_text()) if ort_span else ""
            location = re.sub(r"^Arbeitsort:\s*", "", location)
            start_date = clean_text(date_li.get_text()) if date_li else ""
            salary = clean_text(gehalt_li.get_text()) if gehalt_li else ""

            if not title:
                continue

            vacancies.append({
                "title": f"[Arbeitsagentur] {title}",
                "link": link,
                "company": company,
                "location": location,
                "start_date": start_date,
                "salary": salary,
            })
    except Exception as e:
        print(f"[arbeitsagentur] Ошибка: {e}")
    return vacancies


# ---------------------------------------------------------------------------
# 2. ausbildung.de
# ---------------------------------------------------------------------------
def parse_ausbildung_de():
    url = "https://www.ausbildung.de/suche/"
    params = {
        "search": "Fachinformatiker/in-|Chemnitz",
        "apprenticeshipType": ["Ausbildung", "Schulische und duale Ausbildung"],
    }
    vacancies = []
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=20)
        print(f"[ausbildung.de] status={res.status_code}, len={len(res.text)}")
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=re.compile(r"^/stellen/")):
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.ausbildung.de" + link
            if link in seen:
                continue
            seen.add(link)

            title_el = a.find(attrs={"data-testid": "jp-title"})
            company_el = a.find(attrs={"data-testid": "jp-customer"})
            branches_el = a.find(attrs={"data-testid": "jp-branches"})
            starting_el = a.find(attrs={"data-testid": "jp-starting-at"})
            vacancies_el = a.find(attrs={"data-testid": "jp-vacancies"})

            title = clean_text(title_el.get_text()) if title_el else ""
            company = clean_text(company_el.get_text()) if company_el else "Не указана"
            company = re.sub(r"^bei\s*", "", company)  # убираем "bei " в начале
            location = clean_text(branches_el.get_text()) if branches_el else ""
            start_date = clean_text(starting_el.get_text()) if starting_el else ""
            places = clean_text(vacancies_el.get_text()) if vacancies_el else ""

            if not title:
                continue

            vacancies.append({
                "title": f"[Ausbildung.de] {title}",
                "link": link,
                "company": company,
                "location": location,
                "start_date": start_date,
                "places": places,
            })
    except Exception as e:
        print(f"[ausbildung.de] Ошибка: {e}")
    return vacancies


# ---------------------------------------------------------------------------
# 3. azubi.de — через headless-браузер Playwright
#    (обычный requests.get блокируется Cloudflare на уровне TLS-фингерпринта,
#     возвращая 405; настоящий браузер этот барьер проходит нормально)
#
#    ВНИМАНИЕ: сайт стабильно отдаёт антибот-заглушку даже через Playwright,
#    поэтому вызов этой функции убран из main(), чтобы не тратить время
#    (до 30+ секунд) на заведомо безуспешную попытку. Функция оставлена
#    в коде на случай, если сайт снова станет доступен — тогда достаточно
#    вернуть вызов parse_azubi_de() в список all_jobs ниже.
# ---------------------------------------------------------------------------
def parse_azubi_de():
    from urllib.parse import urlencode

    base_url = ("https://www.azubi.de/beruf/ausbildung-fachinformatiker/"
                "ausbildungsplaetze/stadt/chemnitz")
    params = {
        "text": "Fachinformatiker/in",
        "location": "Chemnitz",
        "radius": "30",
        "apprenticeships[]": "ausbildung-fachinformatiker",
    }
    full_url = base_url + "?" + urlencode(params)

    vacancies = []
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="de-DE",
            )
            page = context.new_page()
            page.goto(full_url, timeout=30000, wait_until="domcontentloaded")

            # ждём появления реальных карточек вакансий, а не просто "сеть затихла"
            try:
                page.wait_for_selector("a[href*='/ausbildungsplatz/']", timeout=15000)
            except Exception:
                print("[azubi.de] Карточки вакансий не появились за 15 секунд — "
                      "вероятно, антибот-заглушка или капча")

            html = page.content()
            page_title = page.title()
            browser.close()

        print(f"[azubi.de] Playwright загрузил страницу, len={len(html)}, "
              f"title='{page_title}'")

        # диагностика: если страница маленькая/подозрительная — печатаем кусок для анализа
        if len(html) < 30000:
            snippet = re.sub(r"<[^>]+>", " ", html)
            snippet = clean_text(snippet)[:400]
            print(f"[azubi.de] Похоже на блокировку/пустую страницу. "
                  f"Текст (первые 400 симв.): {snippet}")

        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=re.compile(r"/ausbildungsplatz/")):
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.azubi.de" + link
            if link in seen:
                continue
            seen.add(link)

            # заголовок: любой из двух одинаковых <h2>...</h2> внутри карточки
            title_el = a.find("h2")
            title = clean_text(title_el.get_text()) if title_el else ""

            # компания: <span> внутри блока "flex flex-wrap items-center gap-xs"
            company = "Не указана"
            company_block = a.find("div", class_=lambda c: c and "flex-wrap" in c and "items-center" in c)
            if company_block:
                company_span = company_block.find("span")
                if company_span:
                    company = clean_text(company_span.get_text())

            # город и дата начала — идут в <li> списке рядом с иконками
            location = ""
            start_date = ""
            li_items = a.find_all("li")
            for li in li_items:
                text = clean_text(li.get_text())
                if re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
                    start_date = text
                elif text:
                    location = text

            if not title:
                continue

            vacancies.append({
                "title": f"[Azubi.de] {title}",
                "link": link,
                "company": company,
                "location": location,
                "start_date": start_date,
            })
    except Exception as e:
        print(f"[azubi.de] Ошибка: {e}")
    return vacancies


# ---------------------------------------------------------------------------
# 4. aubi-plus.de
# ---------------------------------------------------------------------------
def parse_aubi_plus():
    url = "https://www.aubi-plus.de/suchmaschine/suche/"
    params = {
        "fBereich[]": "it-und-edv",
        # "fBeginn[]": "2027",  # раскомментируйте, если нужен только набор 2027 года
        "fLand[]": "deutschland",
        "s[]": "relevanz",
        "aSuggest": "Chemnitz (Chemnitz, Deutschland)",
        "aSuggestLat": "50.835",
        "aSuggestLon": "12.922",
        "mSuggest": "Fachinformatiker/in",
        "fGeo": "75",
        "s": "relevanz",
        "anzahl": "10",
        "fBptl": "0",
        "fBlitzbewerbung": "0",
    }
    vacancies = []
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=20)
        print(f"[aubi-plus] status={res.status_code}, len={len(res.text)}")
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        seen = set()
        # каждая карточка вакансии — <a class="stretched-link" href="/ausbildung/...">
        for a in soup.find_all("a", class_="stretched-link", href=re.compile(r"^/ausbildung/")):
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.aubi-plus.de" + link
            if link in seen:
                continue
            seen.add(link)

            title = clean_text(a.get_text())
            if not title:
                continue

            # карточка целиком — родительский div "col-12 col-sm ..." с рядами row gy-2
            company = "Не указана"
            location = ""
            start_date = ""
            card = a.find_parent("div", class_="row")
            if card:
                # находим col-12 без <h2> и без <i> — там просто <span>Компания</span>
                for col in card.find_all("div", class_="col-12"):
                    if col.find("h2") is None and col.find("i") is None:
                        span = col.find("span")
                        if span:
                            company = clean_text(span.get_text())
                            break

                # город — рядом с иконкой fa-location-dot, дата — с fa-calendar-days
                loc_icon = card.find("i", class_=re.compile(r"fa-location-dot"))
                if loc_icon:
                    loc_span = loc_icon.find_next("span")
                    if loc_span:
                        location = clean_text(loc_span.get_text())

                date_icon = card.find("i", class_=re.compile(r"fa-calendar-days"))
                if date_icon:
                    date_span = date_icon.find_next("span")
                    if date_span:
                        start_date = clean_text(date_span.get_text())

            vacancies.append({
                "title": f"[Aubi-Plus] {title}",
                "link": link,
                "company": company,
                "location": location,
                "start_date": start_date,
            })
    except Exception as e:
        print(f"[aubi-plus] Ошибка: {e}")
    return vacancies


# ---------------------------------------------------------------------------
# 5. Весь интернет — через RSS-канал Google Alerts
#    (Custom Search JSON API закрыт для новых пользователей с 2025 года,
#    поэтому используем сам продукт Google Alerts, а не платный API)
#
#    Настройка (один раз, без кода):
#    1. Зайти на google.com/alerts
#    2. Создать оповещение с запросом:
#       "Ausbildung" "Fachinformatiker" (Chemnitz OR Dresden OR Leipzig)
#    3. "Показать параметры" -> Источники: Все, Регион: Германия,
#       Частота: как можно быстрее, Показывать: Все результаты,
#       Доставлять на: RSS-канал
#    4. Скопировать ссылку на RSS (вида
#       https://www.google.com/alerts/feeds/XXXXX/XXXXX)
#       и сохранить её в секрете GOOGLE_ALERTS_RSS_URL
# ---------------------------------------------------------------------------
def parse_google_alerts():
    feed_url = os.environ.get("GOOGLE_ALERTS_RSS_URL")
    if not feed_url:
        print("[google-alerts] GOOGLE_ALERTS_RSS_URL не задан — пропускаем")
        return []

    vacancies = []
    try:
        res = requests.get(feed_url, headers=HEADERS, timeout=20)
        print(f"[google-alerts] status={res.status_code}, len={len(res.text)}")
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "xml")
        for entry in soup.find_all("entry"):
            link_tag = entry.find("link")
            title_tag = entry.find("title")
            if not link_tag or not link_tag.get("href"):
                continue

            link = link_tag["href"]
            # Google Alerts заворачивает реальную ссылку в редирект-URL
            # вида https://www.google.com/url?...&url=REAL_LINK&...
            m = re.search(r"[?&]url=([^&]+)", link)
            if m:
                from urllib.parse import unquote
                link = unquote(m.group(1))

            title = (clean_text(BeautifulSoup(title_tag.get_text(), "html.parser").get_text())
                     if title_tag else link)
            domain = re.sub(r"^https?://(www\.)?", "", link).split("/")[0]

            vacancies.append({
                "title": f"[{domain}] {title}",
                "link": link,
                "company": "См. по ссылке",
            })
    except Exception as e:
        print(f"[google-alerts] Ошибка: {e}")
    return vacancies


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def send_to_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Ошибка: Секреты Telegram не найдены")
        return

    # ВАЖНО: правильный домен api.telegram.org и префикс /bot перед токеном
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
               "disable_web_page_preview": False}

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"--- Отправка в Telegram (Чат ID: {chat_id}) ---")
        print(f"Статус-код ответа: {response.status_code}")
        print(f"Ответ от API: {response.text}")
        print("---------------------------------------------")
    except Exception as e:
        print(f"Системная ошибка при отправке в ТГ: {e}")


if __name__ == "__main__":
    print("Сбор вакансий...")
    all_jobs = (
        parse_arbeitsagentur()
        + parse_ausbildung_de()
        # parse_azubi_de() намеренно не вызывается: сайт стабильно отдаёт
        # антибот-заглушку даже через Playwright, поэтому запуск только
        # впустую тратит время (до 30+ секунд на попытку).
        + parse_aubi_plus()
        + parse_google_alerts()
    )
    print(f"Всего найдено вакансий на сайтах: {len(all_jobs)}")

    # Определяем, был ли запуск ручным (GitHub Actions прокидывает это
    # автоматически через GITHUB_EVENT_NAME: 'workflow_dispatch' — ручной
    # запуск кнопкой "Run workflow", 'schedule' — по расписанию).
    is_manual_run = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    sent_jobs_file = "sent_jobs.txt"
    if os.path.exists(sent_jobs_file):
        with open(sent_jobs_file, "r", encoding="utf-8") as f:
            sent_links = set(f.read().splitlines())
    else:
        sent_links = set()

    new_links = []
    for job in all_jobs:
        if job["link"] not in sent_links:
            # доп. строки саммари — добавляются, только если поле реально есть
            extra_lines = []
            if job.get("location"):
                extra_lines.append(f"Город: {job['location']}")
            if job.get("start_date"):
                extra_lines.append(f"Начало: {job['start_date']}")
            if job.get("salary"):
                extra_lines.append(f"Зарплата: {job['salary']}")
            if job.get("places"):
                extra_lines.append(f"Мест: {job['places']}")

            extra_text = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

            message = (f"<b>{job['title']}</b>\n\n"
                       f"Компания: {job['company']}"
                       f"{extra_text}\n"
                       f"Ссылка: {job['link']}")
            send_to_telegram(message)
            new_links.append(job["link"])
            print(f"Отправлено в ТГ: {job['title']}")

    if new_links:
        with open(sent_jobs_file, "a", encoding="utf-8") as f:
            for link in new_links:
                f.write(link + "\n")
        print(f"Отправлено новых вакансий: {len(new_links)}")
    else:
        # Новых вакансий действительно нет: сообщаем об этом в Telegram.
        # При ручном запуске формулировка другая — это по сути "тест связи".
        if is_manual_run:
            send_to_telegram("✅ Тест пройден успешно. Новых вакансий нет.")
        else:
            send_to_telegram("Новых вакансий не найдено.")
        print("Новых вакансий не найдено.")
