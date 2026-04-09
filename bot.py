import asyncio
import os
import requests
from telegram import Bot
import time

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

previous_stats = {}
sent_matches = {}
COOLDOWN = 600  # 10 min

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])


def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 20 or minute > 85:
            return None

        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if not ((goals_home == 0 and goals_away == 0) or abs(goals_home - goals_away) == 1):
            return None

        if "statistics" not in match or not match["statistics"]:
            # fallback minimo (senza stats)
            minute = match["fixture"]["status"]["elapsed"]
    
            if minute and 30 <= minute <= 75:
                return ("WATCH", None)
    
         return None

        stats = match["statistics"]
        if len(stats) < 2:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        def safe(v):
            try:
                return int(v) if v else 0
            except:
                return 0

        sot_home = safe(home[0]["value"])
        sot_away = safe(away[0]["value"])
        shots_home = safe(home[2]["value"])
        shots_away = safe(away[2]["value"])
        danger_home = safe(home[9]["value"])
        danger_away = safe(away[9]["value"])

        total_sot = sot_home + sot_away
        total_shots = shots_home + shots_away
        total_danger = danger_home + danger_away

        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_inc = total_danger - prev["danger"]
        shots_inc = total_shots - prev["shots"]

        previous_stats[match_id] = {
            "danger": total_danger,
            "shots": total_shots
        }

        # 🔥 filtro intelligente (NON troppo rigido)
        pressure_ok = False

        if total_sot >= 4 and total_danger >= 25:
            pressure_ok = True

        if total_sot >= 5 and total_shots >= 9:
            pressure_ok = True

        if danger_inc >= 8:
            pressure_ok = True

        if not pressure_ok:
            return None

        # 💣 dominio
        if danger_home >= danger_away:
            dominance = danger_home - danger_away
            team = match["teams"]["home"]["name"]
        else:
            dominance = danger_away - danger_home
            team = match["teams"]["away"]["name"]

        if dominance < 5:
            return None

        # 🚨 ENTRY
        if total_sot >= 5 and (danger_inc >= 4 or shots_inc >= 2):
            return ("ENTRY", team)

        # ⚠️ WATCH
        if danger_inc >= 3 or shots_inc >= 2:
            return ("WATCH", None)

    except:
        return None

    return None


async def main():
    print("🚀 BOT LIVE ATTIVO")

    while True:
        try:
            matches = get_matches()
            print("Match trovati:", len(matches))

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                match_id = match["fixture"]["id"]
                signal, team = result

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                minute = match["fixture"]["status"]["elapsed"]
                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                if signal == "ENTRY":
                    text = (
                        f"🚨 ENTRY\n"
                        f"{home} vs {away}\n"
                        f"⚽ {gh}-{ga}\n"
                        f"⏱ {minute}'\n"
                        f"🔥 {team} spinge\n"
                        f"🎯 Goal possibile"
                    )

                else:
                    text = (
                        f"⚠️ WATCH\n"
                        f"{home} vs {away}\n"
                        f"⏱ {minute}'\n"
                        f"📈 pressione in crescita"
                    )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(30)


asyncio.run(main())
