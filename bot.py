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
COOLDOWN = 900  # 15 min

# --- MATCH ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])


# --- QUOTE NEXT GOAL ---
def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    try:
        data = requests.get(url, headers=headers, timeout=5).json()
        bets = data["response"][0]["bookmakers"][0]["bets"]

        for bet in bets:
            if bet["name"] == "Next Goal":
                values = bet["values"]
                return float(values[0]["odd"]), float(values[1]["odd"])
    except:
        return None

    return None


# --- LOGICA PRO ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        # ⏱ tempo
        if minute is None or minute < 30 or minute > 90:
            return None

        # ⏳ cooldown
        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        # --- stats obbligatorie ---
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

        # 🔥 pressione minima
        if total_sot < 5 or total_shots < 10:
            return None

        # 💣 dominio
        if sot_home > sot_away:
            team = match["teams"]["home"]["name"]
            side = "home"
        else:
            team = match["teams"]["away"]["name"]
            side = "away"

        # 💰 quote
        odds = get_odds(match_id)
        if not odds:
            return None

        home_odd, away_odd = odds
        odd = home_odd if side == "home" else away_odd

        # 🎯 filtro quota PRO
        if odd < 1.8 or odd > 3.5:
            return None

        return ("ENTRY", team, odd)

    except:
        return None

    return None


# --- BOT ---
async def main():
    print("🚀 BOT PROFESSIONALE ATTIVO")

    while True:
        try:
            matches = get_matches()
            print("Match:", len(matches))

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                match_id = match["fixture"]["id"]
                signal, team, odd = result

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                minute = match["fixture"]["status"]["elapsed"]
                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                text = (
                    f"💣 NEXT GOAL PRO\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute}'\n"
                    f"🔥 Team: {team}\n"
                    f"💰 Quota: {odd}\n"
                    f"🎯 PROSSIMO GOAL"
                )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches[match_id] = time.time()

        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(30)


asyncio.run(main())
