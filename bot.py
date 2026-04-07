import asyncio
import requests
from telegram import Bot
import os
import time

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
API_KEY = os.getenv("API_KEY")

previous_stats = {}
sent_matches = {}
COOLDOWN = 600  # 10 minuti

# --- PARTITE LIVE ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data.get("response", [])

# --- QUOTE NEXT GOAL ---
def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        bookmakers = data["response"][0]["bookmakers"]
        bets = bookmakers[0]["bets"]

        for bet in bets:
            if bet["name"] == "Next Goal":
                odds = bet["values"]

                home_odd = float(odds[0]["odd"])
                away_odd = float(odds[1]["odd"])

                return home_odd, away_odd
    except:
        return None

    return None

# --- CHECK MATCH PRO ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 30 or minute > 80:
            return None

        # --- cooldown ---
        now = time.time()
        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if not (
            (goals_home == 0 and goals_away == 0)
            or abs(goals_home - goals_away) == 1
        ):
            return None

        stats = match.get("statistics")
        if not stats:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        # --- STATS ---
        shots_on_target_home = int(home[0]["value"] or 0)
        shots_on_target_away = int(away[0]["value"] or 0)

        shots_home = int(home[2]["value"] or 0)
        shots_away = int(away[2]["value"] or 0)

        dangerous_home = int(home[9]["value"] or 0)
        dangerous_away = int(away[9]["value"] or 0)

        total_shots_on_target = shots_on_target_home + shots_on_target_away
        total_shots = shots_home + shots_away
        total_danger = dangerous_home + dangerous_away

        # --- BASE FILTER ---
        if total_shots_on_target < 6 or total_danger < 35:
            return None

        # --- TREND ---
        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_increase = total_danger - prev["danger"]
        shots_increase = total_shots - prev["shots"]

        previous_stats[match_id] = {
            "danger": total_danger,
            "shots": total_shots,
        }

        if danger_increase < 6 and shots_increase < 3:
            return None

        # --- DOMINANCE ---
        if dangerous_home > dangerous_away:
            dominance = dangerous_home - dangerous_away
            attacking_team = match["teams"]["home"]["name"]
            attacking_side = "home"
        else:
            dominance = dangerous_away - dangerous_home
            attacking_team = match["teams"]["away"]["name"]
            attacking_side = "away"

        if dominance < 12:
            return None

        # --- QUOTE ---
        odds = get_odds(match_id)
        if not odds:
            return None

        home_odd, away_odd = odds
        odd = home_odd if attacking_side == "home" else away_odd

        # --- VALUE FILTER PRO ---
        if odd < 1.50 or odd > 2.10:
            return None

        # --- FINAL ENTRY ---
        if (
            total_shots_on_target >= 8
            and total_danger >= 45
            and (danger_increase >= 8 or shots_increase >= 4)
        ):
            return ("ENTRY", attacking_team, odd)

    except:
        return None

    return None

# --- BOT ---
async def main():
    bot = Bot(token=TOKEN)

    while True:
        matches = get_matches()

        for match in matches:
            match_id = match["fixture"]["id"]

            result = check_match(match)

            if not result:
                continue

            signal, team, odd = result

            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            minute = match["fixture"]["status"]["elapsed"]
            goals_home = match["goals"]["home"]
            goals_away = match["goals"]["away"]

            text = (
                f"🚨 ELITE ENTRY 🚨\n"
                f"{home} vs {away}\n"
                f"⚽ {goals_home}-{goals_away}\n"
                f"⏱ {minute}'\n"
                f"🔥 Team: {team}\n"
                f"💰 Quota: {odd}\n"
                f"📊 Pressione PRO\n"
                f"🎯 NEXT GOAL PROB"
            )

            await bot.send_message(chat_id=CHAT_ID, text=text)

            sent_matches[match_id] = time.time()

        await asyncio.sleep(30)

# --- AVVIO ---
asyncio.run(main())
