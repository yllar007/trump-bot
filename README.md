# Trump Truth Social Market Monitor Bot

Monitoorib Trump'i Truth Social postitusi ja saadab Telegrami turuanalüüse, kasutades Groq AI-d.

## Setup

### Kohalik testimine

1. Loo `.env` fail:
```
GROQ_API_KEY=gsk_...
TELEGRAM_BOT_TOKEN=8778609956:AA...
TELEGRAM_CHAT_ID=1562023922
```

2. Paigalda sõltuvused:
```bash
pip install -r requirements.txt
```

3. Käivita:
```bash
python bot.py
```

### Google Cloud Run deploy

1. Lood GitHub repo ja push'id kood
2. Google Cloud'is: Cloud Run > Create Service
3. Vali GitHub repo
4. Setid environment variables:
   - GROQ_API_KEY
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
5. Deploy!

## Kuidas töötab

1. Bot kontrollib Trump'i postitusi iga 10 sekundit
2. Kiire 8B filter: kas postitus liigutab turge? (JAH/EI)
3. Kui JAH:
   - Saadab postitu Telegrami
   - Saadab 70B analüüsi turuefektist
4. Kui EI: vaikus

## Mudeled

- **mixtral-8x7b-32768** - kiire filter (~0.1s)
- **llama-70b-8192** - põhjalik analüüs (~0.3s)
