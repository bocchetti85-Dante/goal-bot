import asyncio
import os
import requests
from telegram import Bot
import time

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

sent_matches = {}
COOLDOWN = 900

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    return r.json().get("response", [])

def safe_int(v):
    try:
        if v is None:
            return 0
        if isinstance(v, str):
            v = v.replace("%","").strip()
        return int(v)
    except:
        return 0

def check_match(match):
    fixture = match["fixture"]
    match_id = fixture["id"]
    minute = fixture["status"]["elapsed"]

    if minute is None or minute < 30 or minute > 90:
        return None

    now = time.time()
    if match_id in sent_matches:
        if now - sent_matches[match_id] < COOLDOWN:
            return None

    gh = match["goals"]["home"]
    ga = match["goals"]["away"]

    if gh is None or ga is None:
        return None

    # solo partite ancora vive
    if abs(gh - ga) > 1:
        return None

    score = 0

    # timing
    if 55 <= minute <= 80:
        score += 3
    else:
        score += 1

    # punteggio partita
    if gh == ga:
        score += 2
    else:
        score += 1

    # stats bonus se presenti
    stats = match.get("statistics")

    if stats and len(stats) >= 2:
        score += 2

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        total_sot = 0

        for block in [home, away]:
            for row in block:
                t = row.get("type","").lower()
                if t in ["shots on goal","shots on target"]:
                    total_sot += safe_int(row.get("value"))

        if total_sot >= 4:
            score += 2

    # soglie realistiche
    if score >= 6:
        return "ENTRY"

    if score >= 4:
        return "WATCH"

    return None

async def main():
    print("BOT LIVE REALE")

    while True:
        try:
            matches = get_matches()
            print("LIVE:", len(matches))

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                match_id = match["fixture"]["id"]

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                minute = match["fixture"]["status"]["elapsed"]
                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                text = (
                    f"{'🚨 ENTRY' if result=='ENTRY' else '⚠️ WATCH'}\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute}'\n"
                    f"🎯 Possibile prossimo goal"
                )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print("ERRORE:", repr(e))

        await asyncio.sleep(30)

asyncio.run(main())
