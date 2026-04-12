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
previous_stats = {}
COOLDOWN = 600

def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}
    return requests.get(url, headers=headers).json().get("response", [])

def get_odds(fixture_id):
    # opzionale: se non disponibili non blocca
    try:
        url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
        headers = {"x-apisports-key": API_KEY}
        data = requests.get(url, headers=headers, timeout=5).json()
        bets = data["response"][0]["bookmakers"][0]["bets"]

        for bet in bets:
            if bet["name"] == "Next Goal":
                vals = bet["values"]
                return float(vals[0]["odd"]), float(vals[1]["odd"])
    except:
        return None
    return None

def safe(v):
    try:
        return int(v) if v else 0
    except:
        return 0

def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 30 or minute > 90:
            return None

        now = time.time()
        if match_id in sent_matches and now - sent_matches[match_id] < COOLDOWN:
            return None

        score = 0

        # Stats opzionali
        if "statistics" in match and match["statistics"] and len(match["statistics"]) >= 2:
            home = match["statistics"][0]["statistics"]
            away = match["statistics"][1]["statistics"]

            sot_home = safe(home[0]["value"])
            sot_away = safe(away[0]["value"])
            shots_home = safe(home[2]["value"])
            shots_away = safe(away[2]["value"])
            danger_home = safe(home[9]["value"])
            danger_away = safe(away[9]["value"])

            total_sot = sot_home + sot_away
            total_shots = shots_home + shots_away
            total_danger = danger_home + danger_away

            if total_sot >= 4:
                score += 2
            if total_shots >= 10:
                score += 1
            if total_danger >= 25:
                score += 2

            # dominio
            if abs(danger_home - danger_away) >= 8:
                score += 2

            team = match["teams"]["home"]["name"] if danger_home >= danger_away else match["teams"]["away"]["name"]

            # trend
            prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})
            if total_danger - prev["danger"] >= 5:
                score += 2

            previous_stats[match_id] = {
                "danger": total_danger,
                "shots": total_shots
            }

        else:
            # senza stats: non bloccare tutto
            team = match["teams"]["home"]["name"]
            score += 2

        # timing gold zone
        if 55 <= minute <= 75:
            score += 2

        # quote (bonus, non obbligatorie)
        odds = get_odds(match_id)
        odd = None
        if odds:
            odd = min(odds)
            if 1.8 <= odd <= 3.5:
                score += 2

        if score >= 8:
            return ("ENTRY", team, odd, score)

        if score >= 6:
            return ("WATCH", team, odd, score)

    except:
        return None

    return None

async def main():
    print("BOT SCORING ATTIVO")

    while True:
        try:
            matches = get_matches()

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                match_id = match["fixture"]["id"]
                signal, team, odd, score = result

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
                    f"🔥 Team: {team}\n"
                    f"📊 Score: {score}"
                )

                if odd:
                    text += f"\n💰 Quota: {odd}"

                await bot.send_message(chat_id=CHAT_ID, text=text)
                sent_matches[match_id] = time.time()

        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(30)

asyncio.run(main())
