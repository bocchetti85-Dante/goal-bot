import asyncio
import requests
from telegram import Bot
import os

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
API_KEY = os.getenv("API_KEY")

previous_stats = {}
sent_matches = set()

# --- PARTITE LIVE ---
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data["response"]

# --- LOGICA PRO ---
def check_match(match):
    try:
        fixture = match["fixture"]
        match_id = fixture["id"]
        minute = fixture["status"]["elapsed"]

        # ❌ niente minuto = skip
        if minute is None:
            return None

        # ⏱️ FILTRO TEMPO
        if minute < 25 or minute > 85:
            return None

        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        # ⚽ FILTRO RISULTATO
        if not (goals_home == 0 and goals_away == 0) and not (abs(goals_home - goals_away) == 1):
            return None

        stats = match.get("statistics")
        if not stats or len(stats) < 2:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        def safe_int(val):
            try:
                return int(val) if val is not None else 0
            except:
                return 0

        shots_on_target_home = safe_int(home[0]["value"])
        shots_on_target_away = safe_int(away[0]["value"])

        shots_home = safe_int(home[2]["value"])
        shots_away = safe_int(away[2]["value"])

        dangerous_home = safe_int(home[9]["value"])
        dangerous_away = safe_int(away[9]["value"])

        total_shots_on_target = shots_on_target_home + shots_on_target_away
        total_shots = shots_home + shots_away
        total_danger = dangerous_home + dangerous_away

        # 📈 TREND
        prev = previous_stats.get(match_id, {"danger": 0, "shots": 0})

        danger_increase = total_danger - prev["danger"]
        shots_increase = total_shots - prev["shots"]

        previous_stats[match_id] = {
            "danger": total_danger,
            "shots": total_shots
        }

        # 🔥 DOMINIO
        if dangerous_home >= dangerous_away:
            dominance = dangerous_home - dangerous_away
            attacking_team = match["teams"]["home"]["name"]
        else:
            dominance = dangerous_away - dangerous_home
            attacking_team = match["teams"]["away"]["name"]

        # =========================
        # 💣 FILTRO PROFESSIONALE
        # =========================

        pressure_ok = False

        # metodo classico
        if total_shots_on_target >= 6 and total_danger >= 35:
            pressure_ok = True

        # 🔥 override PRO (salva partite forti)
        if total_shots_on_target >= 5 and total_shots >= 10:
            pressure_ok = True

        # altro override (trend forte)
        if danger_increase >= 10 or shots_increase >= 5:
            pressure_ok = True

        if not pressure_ok:
            return None

        # =========================
        # 🚨 ENTRY
        # =========================
        if total_shots_on_target >= 7 and dominance >= 8:
            if danger_increase >= 5 or shots_increase >= 3:
                return ("ENTRY", attacking_team)

        # =========================
        # ⚠️ WATCH
        # =========================
        if danger_increase >= 4 or shots_increase >= 2:
            return ("WATCH", None)

    except:
        return None

    return None

# --- BOT ---
async def main():
    bot = Bot(token=TOKEN)

    while True:
        try:
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
                        f"📈 Pressione ALTA\n"
                        f"👉 GOAL IMMINENTE\n"
                        f"💰 ENTRA ORA"
                    )

                elif signal == "WATCH":
                    text = (
                        f"⚠️ MATCH CALDO\n"
                        f"{home} vs {away}\n"
                        f"⏱ {minute}'\n"
                        f"📈 Pressione in crescita"
                    )

                await bot.send_message(chat_id=CHAT_ID, text=text)

                sent_matches.add(match_id)

        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(30)

# --- AVVIO ---
asyncio.run(main())
