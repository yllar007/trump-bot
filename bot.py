import os
import time
import threading
import xml.etree.ElementTree as ET
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# API võtmed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# RSS allikad
RSS_URL = "https://trump-proxy.yllar007.workers.dev"  # Trump RSS proxy
WH_SCRAPE_URL = "https://trump-proxy.yllar007.workers.dev/?url=https://www.whitehouse.gov/news/"  # White House otse
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Globaalsed muutujad
GROQ_MODEL = "llama-3.3-70b-versatile"
last_error_time = {}
model_last_refresh = None
seen_ids = set()
seen_wh_ids = set()

ERROR_THROTTLE_SECONDS = 300
MODEL_REFRESH_INTERVAL = 86400

# ─── Groq mudeli valik ───────────────────────────────────────────────────────

def get_best_groq_model():
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10
        )
        models = [m["id"] for m in response.json()["data"]]
        print(f"Saadaolevad mudelid: {models}")
        preferred = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama3-70b-8192",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
        ]
        for model in preferred:
            if model in models:
                print(f"Kasutan mudelit: {model}")
                return model
        llama_models = [m for m in models if "llama" in m.lower()]
        if llama_models:
            return llama_models[0]
        return models[0]
    except Exception as e:
        print(f"Mudeli vali viga: {e}, kasutan default")
        return "llama-3.3-70b-versatile"

# ─── Telegram ────────────────────────────────────────────────────────────────

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram viga: {type(e).__name__}: {e}")
        return False

def send_error_alert(error_key: str, message: str):
    global last_error_time
    now = time.time()
    if error_key in last_error_time:
        if now - last_error_time[error_key] < ERROR_THROTTLE_SECONDS:
            return
    last_error_time[error_key] = now
    send_telegram_message(f"⚠️ <b>TRUMP BOT VIGA</b>\n\n{message}")

# ─── Groq ────────────────────────────────────────────────────────────────────

def groq_request(messages: list, max_tokens: int = 800) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    print(f"Groq HTTP status: {response.status_code}")
    if response.status_code != 200:
        print(f"Groq error: {response.text}")
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def quick_filter(text: str, source: str = "trump") -> bool:
    try:
        result = groq_request(
            max_tokens=10,
            messages=[{"role": "user", "content": f"""Analyze this post. Is it market-moving? Reply with ONE word only: YES or NO

Post: "{text}"

Market-moving: tariffs, taxes, military, forex, stocks, oil, gold, sanctions, deals, Iran, trade, NATO, Fed, economy, executive order, policy change.
NOT market-moving: birthdays, memes, emotions, personal, sports, ceremonies."""}]
        )
        response_text = result.strip().upper()
        print(f"Filter vastus ({source}): '{response_text}'")
        return "YES" in response_text or "JAH" in response_text
    except Exception as e:
        print(f"Filter viga: {type(e).__name__}: {e}")
        send_error_alert("groq_filter", f"Groq filter ebaonnestus:\n{type(e).__name__}: {e}")
        return False

def analyze_market_impact(text: str, source: str = "trump") -> str:
    source_label = "TRUMP TRUTH SOCIAL" if source == "trump" else "WHITE HOUSE"
    try:
        result = groq_request(
            max_tokens=800,
            messages=[{"role": "user", "content": f"""You are a financial analyst. Analyze the potential market impact of this {source_label} post. Reply in Estonian.

POST:
"{text}"

FORMAT (HTML):
<b>TURUMÕJU ANALÜÜS</b>
<b>📊 Indeksid:</b>
- US30: [↑/↓ %]
- S&P 500: [↑/↓ %]
- NASDAQ: [↑/↓ %]

<b>💰 Kaubad:</b>
- Kuld: [↑/↓ %]
- Nafta: [↑/↓ %]
- DXY: [↑/↓ %]

<b>🪙 Krüpto:</b>
- Bitcoin: [↑/↓ %]

<b>📝 KOKKUVÕTE:</b>
[Lühike analüüs]"""}]
        )
        return result
    except Exception as e:
        print(f"Analyys viga: {type(e).__name__}: {e}")
        send_error_alert("groq_analysis", f"Groq analyys ebaonnestus:\n{type(e).__name__}: {e}")
        return "Analyys ebaonnestus"

# ─── Trump RSS ───────────────────────────────────────────────────────────────

def get_trump_posts():
    try:
        response = requests.get(RSS_URL, timeout=15)
        if response.status_code != 200:
            print(f"Trump RSS viga: {response.status_code}")
            send_error_alert("rss_error", f"Trump RSS proxy tagastas: {response.status_code}")
            return []

        root = ET.fromstring(response.text)
        posts = []
        for item in root.findall(".//item"):
            guid = item.findtext("guid", "")
            title = item.findtext("title", "")
            pub_date = item.findtext("pubDate", "")

            if not title or "[No Title]" in title:
                continue

            posts.append({
                "id": guid,
                "content": title,
                "pub_date": pub_date
            })

        return posts[:10]

    except Exception as e:
        print(f"Trump RSS viga: {type(e).__name__}: {e}")
        send_error_alert("rss_exception", f"Trump RSS viga:\n{type(e).__name__}: {e}")
        return []

# ─── White House scraper ──────────────────────────────────────────────────────

def get_whitehouse_posts():
    try:
        response = requests.get(WH_SCRAPE_URL, timeout=15)
        if response.status_code != 200:
            print(f"WH viga: {response.status_code}")
            send_error_alert("wh_error", f"White House tagastas: {response.status_code}")
            return []

        html = response.text
        posts = []
        import re as _re

        # whitehouse.gov uudiste lingid: /releases/, /briefings-statements/,
        # /presidential-actions/, /fact-sheets/, /remarks/
        pattern = _re.compile(
            r'href="(https://www\.whitehouse\.gov/(?:releases|briefings-statements|presidential-actions|fact-sheets|remarks)/[^"]+)"[^>]*>\s*([^<]{15,200}?)\s*</a>',
            _re.DOTALL
        )

        seen_urls = set()
        for match in pattern.finditer(html):
            url = match.group(1)
            title = match.group(2).strip()

            if url in seen_urls:
                continue
            if '\n' in title or len(title) < 15:
                continue
            if any(skip in title.lower() for skip in ['read more', 'view all', 'see all', 'learn more']):
                continue

            seen_urls.add(url)
            posts.append({
                "id": url,
                "content": title,
                "pub_date": ""
            })

        print(f"🏛️ White House: {len(posts)} postitust leitud")
        return posts[:15]

    except Exception as e:
        print(f"WH viga: {type(e).__name__}: {e}")
        send_error_alert("wh_exception", f"White House viga:\n{type(e).__name__}: {e}")
        return []

# ─── Trump monitor ───────────────────────────────────────────────────────────

def monitor_trump():
    global GROQ_MODEL, model_last_refresh, seen_ids

    print("Trump Bot kaivitatud...")
    GROQ_MODEL = get_best_groq_model()
    model_last_refresh = time.time()

    send_telegram_message(
        f"🤖 <b>Trump Bot käivitatud!</b>\n"
        f"Mudel: {GROQ_MODEL}\n"
        f"Monitoorin Trump'i postitusi + White House uudiseid..."
    )

    print("Laen olemasolevad Trump postitused...")
    existing = get_trump_posts()
    for post in existing:
        seen_ids.add(post["id"])
    print(f"{len(seen_ids)} olemasolevat Trump postitust salvestatud, ootan uusi...")

    consecutive_empty = 0

    while True:
        try:
            now = time.time()

            if now - model_last_refresh >= MODEL_REFRESH_INTERVAL:
                new_model = get_best_groq_model()
                if new_model != GROQ_MODEL:
                    send_telegram_message(f"🔄 Groq mudel uuendatud: {GROQ_MODEL} → {new_model}")
                    GROQ_MODEL = new_model
                model_last_refresh = now

            posts = get_trump_posts()

            if not posts:
                consecutive_empty += 1
                print(f"Trump postitusi ei saadud ({consecutive_empty}x), ootan...")
                if consecutive_empty >= 10:
                    send_error_alert("rss_empty", "Trump RSS ei tagasta postitusi juba 5 minutit!")
                time.sleep(30)
                continue

            consecutive_empty = 0

            for post in posts:
                post_id = post["id"]
                content = post["content"].strip()

                if post_id in seen_ids or not content:
                    continue

                seen_ids.add(post_id)
                print(f"UUS Trump postitus: {content[:100]}...")

                if quick_filter(content, source="trump"):
                    print("Trump postitus labis filtri - analyysime...")
                    telegram_text = (
                        f"<b>🔴 TRUMP TRUTH SOCIAL</b>\n\n"
                        f"{content}\n\n"
                        f"<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                    )
                    send_telegram_message(telegram_text)
                    analysis = analyze_market_impact(content, source="trump")
                    send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                else:
                    print("Trump postitus ei liiguta turge - vaikus")

            time.sleep(5)

        except Exception as e:
            print(f"Trump loop viga: {type(e).__name__}: {e}")
            send_error_alert("main_loop", f"Trump loop viga:\n{type(e).__name__}: {e}")
            time.sleep(30)

# ─── White House monitor ─────────────────────────────────────────────────────

def monitor_whitehouse():
    global seen_wh_ids

    print("White House monitor kaivitatud...")

    print("Laen olemasolevad White House postitused...")
    existing = get_whitehouse_posts()
    for post in existing:
        seen_wh_ids.add(post["id"])
    print(f"{len(seen_wh_ids)} olemasolevat WH postitust salvestatud, ootan uusi...")

    while True:
        try:
            posts = get_whitehouse_posts()

            if not posts:
                print("WH postitusi ei saadud, ootan...")
                time.sleep(60)
                continue

            for post in posts:
                post_id = post["id"]
                content = post["content"].strip()

                if post_id in seen_wh_ids or not content:
                    continue

                seen_wh_ids.add(post_id)
                print(f"UUS White House postitus: {content[:100]}...")

                if quick_filter(content, source="whitehouse"):
                    print("WH postitus labis filtri - analyysime...")
                    telegram_text = (
                        f"<b>🏛️ WHITE HOUSE</b>\n\n"
                        f"{content}\n\n"
                        f"<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                    )
                    send_telegram_message(telegram_text)
                    analysis = analyze_market_impact(content, source="whitehouse")
                    send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                else:
                    print("WH postitus ei liiguta turge - vaikus")

            time.sleep(5)

        except Exception as e:
            print(f"WH loop viga: {type(e).__name__}: {e}")
            send_error_alert("wh_loop", f"White House loop viga:\n{type(e).__name__}: {e}")
            time.sleep(60)

# ─── HTTP server ─────────────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/test":
            print("Test endpoint kaivitatud...")
            test_post = "Trump: We are imposing 25% tariffs on ALL imports from China starting Monday!"
            if quick_filter(test_post):
                telegram_text = (
                    f"<b>🔴 TRUMP TRUTH SOCIAL</b>\n\n"
                    f"{test_post}\n\n"
                    f"<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                )
                send_telegram_message(telegram_text)
                analysis = analyze_market_impact(test_post)
                send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Test OK - vaata Telegrami!")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Filter blokkis - midagi valesti")
        elif self.path == "/status":
            status = (
                f"Bot: OK\n"
                f"Mudel: {GROQ_MODEL}\n"
                f"Trump seen IDs: {len(seen_ids)}\n"
                f"WH seen IDs: {len(seen_wh_ids)}\n"
                f"Aeg: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(status.encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Trump Bot OK - running")

    def log_message(self, format, *args):
        pass

# ─── Käivitus ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"HTTP server kaivitatud pordil {port}")

    # Trump monitor
    threading.Thread(target=monitor_trump, daemon=True).start()

    # White House monitor
    threading.Thread(target=monitor_whitehouse, daemon=True).start()

    server.serve_forever()
