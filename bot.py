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
COOLDOWN = 600

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    return r.json().get("response", [])

def stat_value(stats_list, names):
    for row in stats_list:
        t = row.get("type", "").lower()
        if t in names:
            v = row.get("value")
            try:
                if v is None:
                    return 0
                if isinstance(v, str):
                    v = v.replace("%","").strip()
                return int(v)
            except:
                return 0
    return 0

def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 30 or minute > 90:
            return None

        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        home_name = match["teams"]["home"]["name"]
        away_name = match["teams"]["away"]["name"]

        stats = match.get("statistics")

        # se stats mancanti, segnala comunque WATCH dopo 60'
        if not stats or len(stats) < 2:
            if minute >= 60:
                return ("WATCH", home_name, 3)
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        sot_home = stat_value(home, ["shots on goal","shots on target"])
        sot_away = stat_value(away, ["shots on goal","shots on target"])

        shots_home = stat_value(home, ["total shots","shots total"])
        shots_away = stat_value(away, ["total shots"])

        danger_home = stat_value(home, ["dangerous attacks"])
        danger_away = stat_value(away, ["dangerous attacks"])

        total_sot = sot_home + sot_away
        total_shots = shots_home + shots_away
        total_danger = danger_home + danger_away

        # DEBUG logs
        print(
            f"{home_name} vs {away_name} | "
            f"{minute}' | SOT {total_sot} | SH {total_shots} | DNG {total_danger}"
        )

        score = 0

        if total_sot >= 3:
            score += 2
        if total_shots >= 8:
            score += 2
        if total_danger >= 20:
            score += 2

        # dominio
        if abs(danger_home - danger_away) >= 5:
            score += 2

        # timing
        if 55 <= minute <= 80:
            score += 2

        team = home_name if danger_home >= danger_away else away_name

        if score >= 8:
            return ("ENTRY", team, score)

        if score >= 5:
            return ("WATCH", team, score)

    except Exception as e:
        print("ERRORE CHECK:", e)
        return None

    return None

async def main():
    print("BOT DEBUG LIVE")

    while True:
        try:
            matches = get_matches()
            print("MATCH LIVE:", len(matches))

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                signal, team, score = result

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                minute = match["fixture"]["status"]["elapsed"]
                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                text = (
                    f"{'🚨 ENTRY' if signal=='ENTRY' else '⚠️ WATCH'}\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute}'\n"
                    f"🔥 {team}\n"
                    f"📊 Score {score}"
                )

                await bot.send_message(chat_id=CHAT_ID, text=text)
                sent_matches[match["fixture"]["id"]] = time.time()

        except Exception as e:
            print("ERRORE MAIN:", e)

        await asyncio.sleep(30)

asyncio.run(main())
