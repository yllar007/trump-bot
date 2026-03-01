import os
import requests
import asyncio
from datetime import datetime
from groq import Groq

# API võtmed
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Truth Social API
TRUTH_SOCIAL_API = "https://truthsocial.com/api/v1"
TRUMP_ACCOUNT_ID = "109382633260537656"  # Trump's Truth Social ID

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
    """Kiire 8B filter - kas postitus liigutab turge?"""
    try:
        message = client.messages.create(
            model="mixtral-8x7b-32768",  # Groq 8B mudel
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
        response_text = message.content[0].text.strip().upper()
        return "JAH" in response_text
    except Exception as e:
        print(f"Filter viga: {e}")
        return False

def analyze_market_impact(text: str) -> str:
    """70B mudel teeb põhjalik turuanalüüs"""
    try:
        message = client.messages.create(
            model="llama-70b-8192",  # Groq 70B mudel
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
        return message.content[0].text
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
                
                # Jäta juba nähtud postitused vahele
                if post_id in seen_posts or not content:
                    continue
                
                seen_posts.add(post_id)
                
                # Eemaldame HTML tagid
                content_clean = content.replace("<p>", "").replace("</p>", "")
                
                print(f"📍 Uus postitus: {content_clean[:100]}...")
                
                # KIIRE FILTER
                if quick_filter(content_clean):
                    print("✅ Postitus läbis filtri - analüüsime...")
                    
                    # Saada postitus
                    telegram_text = f"<b>🔴 TRUMP TRUTH SOCIAL</b>\n\n{content_clean}\n\n<i>{datetime.now().strftime('%d.%m.%Y kl %H:%M')}</i>"
                    send_telegram_message(telegram_text)
                    
                    # Saada analüüs
                    analysis = analyze_market_impact(content_clean)
                    send_telegram_message(f"<b>📊 AI TURU ANALÜÜS</b>\n\n{analysis}")
                else:
                    print("⏭️ Postitus ei liiguta turge - vaikus")
            
            # Kontrolli iga 1.5 sekundit
            asyncio.run(asyncio.sleep(1.5))
            
        except Exception as e:
            print(f"❌ Viga: {e}")
            asyncio.run(asyncio.sleep(1.5))

if __name__ == "__main__":
    monitor_trump()
