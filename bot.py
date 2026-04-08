import asyncio
import requests
from telegram import Bot
import os
import time

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
API_KEY = os.getenv("API_KEY")

previous_stats = {}
previous_odds = {}
sent_matches = {}
COOLDOWN = 480  # 8 min

# --- MATCH ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])

# --- ODDS NEXT GOAL ---
def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    try:
        data = requests.get(url, headers=headers, timeout=5).json()
        bets = data["response"][0]["bookmakers"][0]["bets"]

        for bet in bets:
            if bet["name"] == "Next Goal":
                odds = bet["values"]
                return float(odds[0]["odd"]), float(odds[1]["odd"])
    except:
        return None

    return None

# --- LOGICA PRO + EDGE ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        # ⏱ filtro tempo
        if minute is None or minute < 20 or minute > 88:
            return None

        # ⏳ cooldown
        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if not ((goals_home == 0 and goals_away == 0) or abs(goals_home - goals_away) == 1):
            return None

        stats = match.get("statistics")
        if not stats:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        shots_on_target_home = int(home[0]["value"] or 0)
        shots_on_target_away = int(away[0]["value"] or 0)
        shots_home = int(home[2]["value"] or 0)
        shots_away = int(away[2]["value"] or 0)
        dangerous_home = int(home[9]["value"] or 0)
        dangerous_away = int(away[9]["value"] or 0)

        total_sot = shots_on_target_home + shots_on_target_away
        total_shots = shots_home + shots_away
        total_danger = dangerous_home + dangerous_away

        # 🔥 pressione base
        if total_sot < 4 or total_danger < 25:
            return None

        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_inc = total_danger - prev["danger"]
        shots_inc = total_shots - prev["shots"]

        previous_stats[match_id] = {"danger": total_danger, "shots": total_shots}

        # 💣 EDGE PROFESSIONALE (ACCELERAZIONE)
        if danger_inc < 5:
            return None

        # 📈 trend
        if danger_inc < 3 and shots_inc < 1:
            return None

        # 💣 dominio
        if dangerous_home > dangerous_away:
            dominance = dangerous_home - dangerous_away
            team = match["teams"]["home"]["name"]
            side = "home"
        else:
            dominance = dangerous_away - dangerous_home
            team = match["teams"]["away"]["name"]
            side = "away"

        if dominance < 6:
            return None

        # 💰 quote (NON MODIFICATE)
        odds = get_odds(match_id)
        if not odds:
            return None

        home_odd, away_odd = odds
        odd = home_odd if side == "home" else away_odd

        if odd < 1.80 or odd > 3.5:
            return None

        # 📉 movimento quota
        prev_odd = previous_odds.get(match_id, odd)
        odds_drop = prev_odd - odd

        previous_odds[match_id] = odd

        if odds_drop < -0.05:
            return None

        # 🚨 ENTRY
        if total_sot >= 5 and total_danger >= 30:
            if danger_inc >= 4 or shots_inc >= 2:
                return ("ENTRY", team, odd)

    except:
        return None

    return None

# --- BOT ---
async def main():
    bot = Bot(token=TOKEN)

    while True:
        matches = get_matches()

        for match in matches:
            result = check_match(match)

            if not result:
                continue

            match_id = match["fixture"]["id"]
            team, odd = result[1], result[2]

            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            minute = match["fixture"]["status"]["elapsed"]
            goals_home = match["goals"]["home"]
            goals_away = match["goals"]["away"]

            text = (
                f"💣 PRO EDGE SIGNAL 💣\n"
                f"{home} vs {away}\n"
                f"⚽ {goals_home}-{goals_away}\n"
                f"⏱ {minute}'\n"
                f"🔥 Team: {team}\n"
                f"💰 Quota: {odd}\n"
                f"🚀 Accelerazione attacchi\n"
                f"📉 Movimento quota\n"
                f"🎯 NEXT GOAL"
            )

            await bot.send_message(chat_id=CHAT_ID, text=text)

            sent_matches[match_id] = time.time()

        await asyncio.sleep(30)

asyncio.run(main())
