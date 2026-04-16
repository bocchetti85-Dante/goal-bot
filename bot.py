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
    return requests.get(url, headers=headers, timeout=10).json().get("response", [])

def val(stats, names):
    for row in stats:
        t = row.get("type","").lower()
        if t in names:
            try:
                v = row.get("value")
                if v is None:
                    return 0
                return int(str(v).replace("%",""))
            except:
                return 0
    return 0

def check_match(match):
    try:
        minute = match["fixture"]["status"]["elapsed"]
        if minute is None or minute < 45 or minute > 88:
            return None

        match_id = match["fixture"]["id"]

        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        gh = match["goals"]["home"]
        ga = match["goals"]["away"]

        if gh is None or ga is None:
            return None

        if abs(gh - ga) > 2:
            return None

        stats = match.get("statistics")

        # Se stats mancanti ma minuto avanzato
        if not stats or len(stats) < 2:
            if minute >= 70:
                return "LIVE PUSH"
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        sot_h = val(home, ["shots on goal","shots on target"])
        sot_a = val(away, ["shots on goal","shots on target"])

        dang_h = val(home, ["dangerous attacks"])
        dang_a = val(away, ["dangerous attacks"])

        total_sot = sot_h + sot_a

        if total_sot < 4:
            return None

        # Dominio morbido
        if dang_h > dang_a + 5:
            return match["teams"]["home"]["name"]

        if dang_a > dang_h + 5:
            return match["teams"]["away"]["name"]

        # Se equilibrio ma minuto alto
        if minute >= 75 and total_sot >= 6:
            return "MATCH OPEN"

    except:
        return None

    return None

async def main():
    print("BOT BALANCED PRO")

    while True:
        try:
            matches = get_matches()

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
                    f"🚨 ENTRY BALANCED\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute}'\n"
                    f"🔥 Focus: {result}\n"
                    f"🎯 Possibile goal live"
                )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print(e)

        await asyncio.sleep(30)

asyncio.run(main())
