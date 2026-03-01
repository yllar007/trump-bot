🚀 TRUMP BOT - TÄISVALIKU DEPLOYMENT JUHEND

═══════════════════════════════════════════════════════════════

SAMM 1: GitHub'i repo loomine (5 min)
═══════════════════════════════════════════════════════════════

1. Mine: https://github.com/new
2. Repo nimi: trump-bot
3. Description: Trump Truth Social market monitoring bot
4. Vali "Public"
5. Kliki "Create repository"

Nüüd on sul github.com/yllar007/trump-bot repo

═══════════════════════════════════════════════════════════════

SAMM 2: Kood üles laadida (7 min)
═══════════════════════════════════════════════════════════════

VARIANT A: Command line (lihtsaim)

1. Paigalda Git: https://git-scm.com/

2. Ava terminal ja käivita:

git clone https://github.com/yllar007/trump-bot.git
cd trump-bot

3. Kopeeri need failid kausta:
   - bot.py
   - requirements.txt
   - Dockerfile
   - .gitignore
   - .env.example
   - README.md

4. Siis käivita:

git add .
git commit -m "Initial commit: Trump bot"
git branch -M main
git remote add origin https://github.com/yllar007/trump-bot.git
git push -u origin main

(Küsib GitHub username ja personal access token - vt allpool)

VARIANT B: GitHub web interface (kui Git ei toimi)

1. Mine: https://github.com/yllar007/trump-bot
2. Kliki "Add file" > "Create new file"
3. Kopeeri iga faili sisu sinna ükshaaval

═══════════════════════════════════════════════════════════════

SAMM 3: Personal Access Token (GitHub autentimine)
═══════════════════════════════════════════════════════════════

1. Mine: https://github.com/settings/tokens
2. Kliki "Generate new token" > "Generate new token (classic)"
3. Nimi: trump-bot-deploy
4. Vali õigused:
   ✓ repo (kõik)
   ✓ workflow
5. Kliki "Generate token"
6. KOPEERI token (näidatakse ainult korra!)
7. Terminal'is: pasted token parooliküsimuse kohale

═══════════════════════════════════════════════════════════════

SAMM 4: Google Cloud deploy (10 min)
═══════════════════════════════════════════════════════════════

1. Mine: https://console.cloud.google.com/run
   (Peaks olema juba loginud)

2. Kliki "Create Service"

3. Vali "Continuously deploy from a repository"

4. Kliki "SET UP WITH CLOUD BUILD"

5. Vali:
   - GitHub
   - yllar007/trump-bot
   - Branch: main
   - Build type: Dockerfile

6. OLULINE - Environment variables:
   Kliki "Variables and Secrets"
   
   Lisa 3 variable:
   
   GROQ_API_KEY = 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
   TELEGRAM_BOT_TOKEN = 8778609956:AAFr29fjbMEe6AJIQMzOSQZVtlkekQLwt3E
   TELEGRAM_CHAT_ID = 1562023922

7. Service settings:
   - Name: trump-bot
   - Region: us-central1
   - Memory: 512 MB
   - CPU: 1
   - Timeout: 3600 sekundi
   - Execution environment: 2nd gen

8. Kliki "CREATE"

9. Oota deployment (~2-3 minutit)

═══════════════════════════════════════════════════════════════

SAMM 5: Kontrolli, et töötab
═══════════════════════════════════════════════════════════════

1. Mine: https://console.cloud.google.com/run
2. Kliki "trump-bot" service
3. Vaata "Logs" - peaks näitama:
   "🤖 Trump Bot käivitatud..."

4. Trump'i postituse ootel - saada talle Telegrami testisõnum
   (peaks näitama logides)

═══════════════════════════════════════════════════════════════

SAMM 6: Mida teha, kui midagi viltu läheb
═══════════════════════════════════════════════════════════════

PROBLEEM: Build fail
→ Vaata "Build" tab ja vea sõnum
→ Sageli: puudub fail vms

PROBLEEM: Environment variables pole seatud
→ Otsi "Variables" ja kontrolli, et olemas

PROBLEEM: Bot töötab aga ei saada sõnumeid
→ Vaata logid: /console.cloud.google.com/run/trump-bot > Logs
→ Kontrolli, et TELEGRAM_CHAT_ID on õige

PROBLEEM: Groq API error
→ Kontrolli, et GROQ_API_KEY on õige (tasuta konto piirangud?)

═══════════════════════════════════════════════════════════════

✅ VALMIS!

Bot töötab nüüd 24/7 Google Cloud'is.
Trump postitab → ~2-3 sekundit hiljem Telegrami teade.

Kuidas seisab? 👍
