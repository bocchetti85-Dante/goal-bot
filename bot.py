import asyncio
import os
import requests
from telegram import Bot
import time

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

sent_matches = {}
COOLDOWN = 600  # 10 minuti

# 🔥 CAMPIONATI TOP (MODIFICABILE)
TOP_LEAGUES = [
    "UEFA Champions League",
    "UEFA Europa League",
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1"
]

# --- MATCH ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])


# --- LOGICA PRO ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        # ⏱ tempo
        if minute is None or minute < 20 or minute > 85:
            return None

        # ⏳ cooldown
        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        # 🔥 FILTRO CAMPIONATO
        league_name = match["league"]["name"]

        if league_name not in TOP_LEAGUES:
            return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if goals_home is None or goals_away is None:
            return None

        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]

        # --- SE NON CI SONO STATS → SCARTA (PRO)
        if "statistics" not in match or not match["statistics"]:
            return None

        stats = match["statistics"]
        if len(stats) < 2:
            return None

        home_stats = stats[0]["statistics"]
        away_stats = stats[1]["statistics"]

        def safe(v):
            try:
                return int(v) if v else 0
            except:
                return 0

        sot_home = safe(home_stats[0]["value"])
        sot_away = safe(away_stats[0]["value"])
        shots_home = safe(home_stats[2]["value"])
        shots_away = safe(away_stats[2]["value"])

        total_sot = sot_home + sot_away
        total_shots = shots_home + shots_away

        # 💣 ENTRY (segnale forte)
        if total_sot >= 6:
            team = home if sot_home > sot_away else away
            return ("ENTRY", team)

        # ⚠️ WATCH (solo se interessante)
        if total_sot >= 4 and total_shots >= 10:
            return ("WATCH", None)

    except:
        return None

    return None


# --- BOT ---
async def main():
    print("🚀 BOT PRO ATTIVO")

    while True:
        try:
            matches = get_matches()
            print("📊 Match:", len(matches))

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
                        f"🚨 ENTRY PRO\n"
                        f"{home} vs {away}\n"
                        f"⚽ {gh}-{ga}\n"
                        f"⏱ {minute}'\n"
                        f"🔥 {team} domina\n"
                        f"🎯 GOAL IMMINENTE"
                    )
                else:
                    text = (
                        f"⚠️ WATCH PRO\n"
                        f"{home} vs {away}\n"
                        f"⏱ {minute}'\n"
                        f"📈 partita interessante"
                    )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(30)


asyncio.run(main())
