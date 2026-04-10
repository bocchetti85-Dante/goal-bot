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

# --- PRENDE MATCH LIVE ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])


# --- LOGICA SBLOCCATA ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 20 or minute > 85:
            return None

        # ⏳ cooldown
        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if goals_home is None or goals_away is None:
            return None

        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]

        # --- CASO SENZA STATISTICHE ---
        if "statistics" not in match or not match["statistics"]:
            if 30 <= minute <= 75:
                return ("WATCH", None)
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

        # --- LOGICA SEMPLICE MA EFFICACE ---

        # 🚨 ENTRY (forte pressione)
        if total_sot >= 5:
            team = home if sot_home > sot_away else away
            return ("ENTRY", team)

        # ⚠️ WATCH (pressione media)
        if total_sot >= 3 or total_shots >= 8:
            return ("WATCH", None)

    except:
        return None

    return None


# --- BOT ---
async def main():
    print("🚀 BOT LIVE ATTIVO")

    while True:
        try:
            matches = get_matches()
            print("📊 Match trovati:", len(matches))

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
            print("❌ ERRORE:", e)

        await asyncio.sleep(30)


# --- AVVIO ---
asyncio.run(main())
