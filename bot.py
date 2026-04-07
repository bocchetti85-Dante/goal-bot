import asyncio
import requests
from telegram import Bot
import os
import time

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
API_KEY = os.getenv("API_KEY")

previous_stats = {}
sent_matches = {}
COOLDOWN = 480  # 8 minuti

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data.get("response", [])

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
                return float(odds[0]["odd"]), float(odds[1]["odd"])
    except:
        return None

    return None

def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 25 or minute > 85:
            return None

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

        shots_on_target_home = int(home[0]["value"] or 0)
        shots_on_target_away = int(away[0]["value"] or 0)

        shots_home = int(home[2]["value"] or 0)
        shots_away = int(away[2]["value"] or 0)

        dangerous_home = int(home[9]["value"] or 0)
        dangerous_away = int(away[9]["value"] or 0)

        total_shots_on_target = shots_on_target_home + shots_on_target_away
        total_shots = shots_home + shots_away
        total_danger = dangerous_home + dangerous_away

        # 🔥 FILTRO PIÙ MORBIDO
        if total_shots_on_target < 5 or total_danger < 30:
            return None

        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_increase = total_danger - prev["danger"]
        shots_increase = total_shots - prev["shots"]

        previous_stats[match_id] = {
            "danger": total_danger,
            "shots": total_shots,
        }

        # 📈 TREND PIÙ ACCESSIBILE
        if danger_increase < 4 and shots_increase < 2:
            return None

        # 💣 DOMINIO
        if dangerous_home > dangerous_away:
            dominance = dangerous_home - dangerous_away
            attacking_team = match["teams"]["home"]["name"]
            side = "home"
        else:
            dominance = dangerous_away - dangerous_home
            attacking_team = match["teams"]["away"]["name"]
            side = "away"

        if dominance < 8:
            return None

        # 💰 QUOTE
        odds = get_odds(match_id)
        if not odds:
            return None

        home_odd, away_odd = odds
        odd = home_odd if side == "home" else away_odd

        # 🎯 RANGE PIÙ LARGO
        if odd < 1.40 or odd > 2.40:
            return None

        # 🚨 ENTRY
        if (
            total_shots_on_target >= 6
            and total_danger >= 35
            and (danger_increase >= 5 or shots_increase >= 3)
        ):
            return ("ENTRY", attacking_team, odd)

    except:
        return None

    return None

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
                f"🔥 ENTRY BALANCED 🔥\n"
                f"{home} vs {away}\n"
                f"⚽ {goals_home}-{goals_away}\n"
                f"⏱ {minute}'\n"
                f"💣 Attacco: {team}\n"
                f"💰 Quota: {odd}\n"
                f"📈 Pressione + Trend\n"
                f"🎯 NEXT GOAL"
            )

            await bot.send_message(chat_id=CHAT_ID, text=text)

            sent_matches[match_id] = time.time()

        await asyncio.sleep(30)

asyncio.run(main())
