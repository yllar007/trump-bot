import os
import re
import time
import threading
import xml.etree.ElementTree as ET
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from groq import Groq

# API võtmed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# RSS proxy läbi Cloudflare Workeri (väldib Truth Social bloki)
RSS_URL = "https://trump-proxy.yllar007.workers.dev"

client = Groq(api_key=GROQ_API_KEY)

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram viga: {e}")
        return False

def get_trump_posts():
    try:
        response = requests.get(RSS_URL, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ RSS viga: {response.status_code}")
            return []

        root = ET.fromstring(response.text)
        posts = []
        for item in root.findall(".//item"):
            guid = item.findtext("guid", "")
            title = item.findtext("title", "")
            pub_date = item.findtext("pubDate", "")

            # Jäta tühjad postitused vahele
            if not title or "[No Title]" in title:
                continue

            posts.append({
                "id": guid,
                "content": title,
                "pub_date": pub_date
            })

        return posts[:10]  # võta 10 viimast

    except Exception as e:
        print(f"RSS viga: {e}")
        return []

def quick_filter(text: str) -> bool:
    try:
        message = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            max_tokens=50,
            messages=[{"role": "user", "content": f"""Analüüsi see postitus. Kas see on turgu liigutav? Vasta AINULT ühe sõnaga: JAH või EI

Postitus: "{text}"

Turgu liigutavad: tariifid, maksud, sõjalisus, forex, börs, nafta, kuld, sanktsioonid, tehingud, aktsiad, Iran, kaubandus, NATO.
Turgu EI liiguta: sünnipäevad, meemid, emotsioonid, isiklikud asjad, sport."""}]
        )
        response_text = message.choices[0].message.content.strip().upper()
        return "JAH" in response_text
    except Exception as e:
        print(f"Filter viga: {e}")
        return False

def analyze_market_impact(text: str) -> str:
    try:
        message = client.chat.completions.create(
            model="llama3-70b-8192",
            max_tokens=800,
            messages=[{"role": "user", "content": f"""Sa oled finantsanalütik. Analüüsi selle Trump postituse potentsiaalne turuefekt.

POSTITUS:
"{text}"

ANALÜÜSI FORMAAT (HTML):
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
        return message.choices[0].message.content
    except Exception as e:
        print(f"Analüüs viga: {e}")
        return "Analüüs ebaõnnestus"

def monitor_trump():
    print("🤖 Trump Bot käivitatud...")
    send_telegram_message("🤖 Trump Bot käivitatud! Monitoorin Trump'i postitusi RSS kaudu...")
    seen_ids = set()

    # Lae kõigepealt olemasolevad postitused seen_ids-i (ei saada vanu)
    print("📋 Laen olemasolevad postitused...")
    existing = get_trump_posts()
    for post in existing:
        seen_ids.add(post["id"])
    print(f"✅ {len(seen_ids)} olemasolevat postitust salvestatud, ootan uusi...")

    while True:
        try:
            posts = get_trump_posts()

            if not posts:
                print("⚠️ Postitusi ei saadud, ootan...")
                time.sleep(30)
                continue

            for post in posts:
                post_id = post["id"]
                content = post["content"].strip()

                if post_id in seen_ids or not content:
                    continue

                seen_ids.add(post_id)
                print(f"🆕 UUS postitus: {content[:100]}...")

                if quick_filter(content):
                    print("✅ Postitus läbis filtri - analüüsime...")
                    telegram_text = (
                        f"<b>🔴 TRUMP TRUTH SOCIAL</b>\n\n"
                        f"{content}\n\n"
                        f"<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                    )
                    send_telegram_message(telegram_text)
                    analysis = analyze_market_impact(content)
                    send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                else:
                    print("⏭️ Postitus ei liiguta turge - vaikus")

            time.sleep(5)  # kontrolli iga 5 sekundi järel

        except Exception as e:
            print(f"❌ Viga: {e}")
            time.sleep(30)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Trump Bot OK - running")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🌐 HTTP server käivitatud pordil {port}")

    bot_thread = threading.Thread(target=monitor_trump, daemon=True)
    bot_thread.start()

    server.serve_forever()
