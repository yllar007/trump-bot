import os
import requests
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from groq import Groq

# API võtmed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Truth Social API
TRUTH_SOCIAL_API = "https://truthsocial.com/api/v1"
TRUMP_ACCOUNT_ID = "109382633260537656"

client = Groq(api_key=GROQ_API_KEY)

def send_telegram_message(text: str):
    """Saadab sõnumi Telegrami"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram viga: {e}")
        return False

def get_trump_posts():
    """Võtab Trump'i uusimad postitused Truth Social'ist"""
    try:
        url = f"{TRUTH_SOCIAL_API}/accounts/{TRUMP_ACCOUNT_ID}/statuses"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            posts = response.json()
            return posts[:5] if isinstance(posts, list) else []
        return []
    except Exception as e:
        print(f"Truth Social viga: {e}")
        return []

def quick_filter(text: str) -> bool:
    """Kiire filter - kas postitus liigutab turge?"""
    try:
        message = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analüüsi see postitus. Kas see on turgu liigutav? Vasta AINULT ühe sõnaga: JAH või EI

Postitus: "{text}"

Turgu liigutavad: tariifid, maksud, sõjalisus, forex, börs, nafta, kuld, sanktsioonid, tehingud, aktsiad.
Turgu EI liiguta: sünnipäevad, meemid, emotsioonid, isiklikud asjad."""
                }
            ]
        )
        response_text = message.choices[0].message.content.strip().upper()
        return "JAH" in response_text
    except Exception as e:
        print(f"Filter viga: {e}")
        return False

def analyze_market_impact(text: str) -> str:
    """70B mudel teeb põhjaliku turuanalüüsi"""
    try:
        message = client.chat.completions.create(
            model="llama-70b-8192",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": f"""Sa oled finantsanalütik. Analüüsi selle Trump postituse potentsiaalne turuefekt.

POSTITUS:
"{text}"

ANALÜÜSI FORMAAT (HTML):
<b>TURUMÕJU ANALÜÜS</b>
<b>📊 Indeksid (eeldatav liikumine):</b>
- US30 (Dow Jones): [↑/↓ %]
- S&P 500: [↑/↓ %]
- NASDAQ: [↑/↓ %]

<b>💰 Kaubad:</b>
- Kuld (XAU/USD): [↑/↓ %]
- Nafta (WTI): [↑/↓ %]
- Valuuta (DXY): [↑/↓ %]

<b>🪙 Krüpto:</b>
- Bitcoin: [↑/↓ %]

<b>📝 KOKKUVÕTE:</b>
[Lühike analüüs, miks need liikumised]

Pea meeles: RISK-OFF = aktsiad ↓, kuld ↑, nafta ↑"""
                }
            ]
        )
        return message.choices[0].message.content
    except Exception as e:
        print(f"Analüüs viga: {e}")
        return "Analüüs ebaõnnestus"

def monitor_trump():
    """Peamine monitoorimise funktsioon"""
    print("🤖 Trump Bot käivitatud...")
    seen_posts = set()

    while True:
        try:
            posts = get_trump_posts()

            for post in posts:
                post_id = post.get("id")
                content = post.get("content", "").strip()

                if post_id in seen_posts or not content:
                    continue

                seen_posts.add(post_id)

                content_clean = content.replace("<p>", "").replace("</p>", "")

                print(f"📍 Uus postitus: {content_clean[:100]}...")

                if quick_filter(content_clean):
                    print("✅ Postitus läbis filtri - analüüsime...")

                    telegram_text = f"<b>🔴 TRUMP TRUTH SOCIAL</b>\n\n{content_clean}\n\n<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                    send_telegram_message(telegram_text)

                    analysis = analyze_market_impact(content_clean)
                    send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                else:
                    print("⏭️ Postitus ei liiguta turge - vaikus")

            # Kontrolli iga 1.5 sekundit
            time.sleep(1.5)

        except Exception as e:
            print(f"❌ Viga: {e}")
            time.sleep(1.5)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Käivita HTTP server eraldi threadis
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    print(f"🌐 HTTP server käivitatud pordil {os.getenv('PORT', 8080)}")
    # Käivita bot
    monitor_trump()
