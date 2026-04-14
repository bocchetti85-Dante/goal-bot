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
COOLDOWN = 1200

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
        if minute is None or minute < 55 or minute > 85:
            return None

        match_id = match["fixture"]["id"]

        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        gh = match["goals"]["home"]
        ga = match["goals"]["away"]

        # partita viva
        if abs(gh - ga) > 1:
            return None

        stats = match.get("statistics")
        if not stats or len(stats) < 2:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        sot_h = val(home, ["shots on goal","shots on target"])
        sot_a = val(away, ["shots on goal","shots on target"])

        dang_h = val(home, ["dangerous attacks"])
        dang_a = val(away, ["dangerous attacks"])

        total_sot = sot_h + sot_a

        # pressione vera
        if total_sot < 5:
            return None

        # dominio
        if dang_h > dang_a + 8:
            team = match["teams"]["home"]["name"]
        elif dang_a > dang_h + 8:
            team = match["teams"]["away"]["name"]
        else:
            return None

        return team

    except:
        return None

async def main():
    print("BOT ENTRY PRO")

    while True:
        try:
            matches = get_matches()

            for match in matches:
                team = check_match(match)

                if not team:
                    continue

                match_id = match["fixture"]["id"]

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                minute = match["fixture"]["status"]["elapsed"]
                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                text = (
                    f"🚨 ENTRY PRO\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute}'\n"
                    f"🔥 Dominio: {team}\n"
                    f"🎯 Probabile prossimo goal"
                )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print(e)

        await asyncio.sleep(30)

asyncio.run(main())
