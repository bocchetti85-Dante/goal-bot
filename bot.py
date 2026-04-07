import asyncio
import requests
from telegram import Bot
import os

# --- CONFIG (da Railway Variables) ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
API_KEY = os.getenv("API_KEY")

previous_stats = {}
previous_odds = {}
sent_matches = set()

# --- PARTITE LIVE ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data["response"]

# --- QUOTE LIVE ---
def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    try:
        bookmakers = data["response"][0]["bookmakers"]
        bets = bookmakers[0]["bets"]

        for bet in bets:
            if bet["name"] == "Match Winner":
                odds = bet["values"]

                home_odd = float(odds[0]["odd"])
                draw_odd = float(odds[1]["odd"])
                away_odd = float(odds[2]["odd"])

                return home_odd, draw_odd, away_odd
    except:
        return None

    return None

# --- LOGICA ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        # 💰 PRENDO QUOTE
        odds = get_odds(match_id)
        if not odds:
            return None

        home_odd, draw_odd, away_odd = odds

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        stats = match["statistics"]
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

        # ⏱ filtro tempo
        if minute < 30 or minute > 80:
            return None

        # ⚽ filtro risultato
        if goals_home == 0 and goals_away == 0:
            pass
        elif abs(goals_home - goals_away) == 1:
            pass
        else:
            return None

        # 🔥 pressione base
        if total_shots_on_target < 5 or total_danger < 30:
            return None

        # 📈 trend
        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_increase = total_danger - prev["danger"]
        shots_increase = total_shots - prev["shots"]

        previous_stats[match_id] = {
            "danger": total_danger,
            "shots": total_shots
        }

        # 💣 DOMINIO
        if dangerous_home > dangerous_away:
            dominance = dangerous_home - dangerous_away
            attacking_team = match["teams"]["home"]["name"]
            team_odd = home_odd
        else:
            dominance = dangerous_away - dangerous_home
            attacking_team = match["teams"]["away"]["name"]
            team_odd = away_odd

        # 💰 FILTRO QUOTE
        if team_odd < 1.40:
            return None

        if team_odd > 3.50:
            return None

        # 📉 MOVIMENTO QUOTE
        prev_odd = previous_odds.get(match_id, team_odd)
        odds_drop = prev_odd - team_odd

        previous_odds[match_id] = team_odd

        if odds_drop <= 0:
            return None

        # 🚨 ENTRY
        if total_shots_on_target >= 7 and total_danger >= 40:
            if dominance >= 10:
                if danger_increase >= 8 or shots_increase >= 4:
                    return ("ENTRY", attacking_team)

        # ⚠️ WATCH
        if danger_increase >= 5 or shots_increase >= 3:
            return ("WATCH", None)

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

            if match_id in sent_matches:
                continue

            result = check_match(match)

            if not result:
                continue

            signal, team = result

            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            minute = match["fixture"]["status"]["elapsed"]
            goals_home = match["goals"]["home"]
            goals_away = match["goals"]["away"]

            if signal == "ENTRY":
                text = (
                    f"🚨🚨 ENTRY ORA 🚨🚨\n"
                    f"{home} vs {away}\n"
                    f"⚽ {goals_home}-{goals_away}\n"
                    f"⏱ {minute}'\n"
                    f"🔥 Dominio: {team}\n"
                    f"📉 Quota in calo\n"
                    f"💰 ENTRA ORA"
                )

            elif signal == "WATCH":
                text = (
                    f"⚠️ MATCH DA TENERE D'OCCHIO\n"
                    f"{home} vs {away}\n"
                    f"⏱ {minute}'\n"
                    f"📈 Pressione in crescita"
                )

            await bot.send_message(chat_id=CHAT_ID, text=text)

            sent_matches.add(match_id)

        await asyncio.sleep(30)

# --- AVVIO ---
asyncio.run(main())
