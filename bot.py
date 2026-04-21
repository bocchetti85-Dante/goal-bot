import asyncio
import os
import requests
import time
from telegram import Bot

# =====================================
# CONFIG
# =====================================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

CHECK_INTERVAL = 30
COOLDOWN = 600  # 10 minuti tra segnali stessa partita

sent_matches = {}

# =====================================
# API LIVE MATCHES
# =====================================
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("response", [])
    except:
        return []


# =====================================
# LETTURA STATISTICHE
# =====================================
def stat(stats, names):
    for row in stats:
        t = row.get("type", "").lower()

        if t in names:
            try:
                v = row.get("value")

                if v is None:
                    return 0

                if isinstance(v, str):
                    v = v.replace("%", "").strip()

                return int(v)

            except:
                return 0

    return 0


# =====================================
# FILTRO PROFESSIONALE (COME FOTO)
# =====================================
def analyze_match(match):
    try:
        fixture = match["fixture"]
        minute = fixture["status"]["elapsed"]

        if minute is None or minute < 77:
            return None

        gh = match["goals"]["home"]
        ga = match["goals"]["away"]

        if gh is None or ga is None:
            return None

        total_goals = gh + ga

        # Goals ≤ 2
        if total_goals > 2:
            return None

        stats = match.get("statistics")

        if not stats or len(stats) < 2:
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        # xG
        xg_h = stat(home, ["expected goals"])
        xg_a = stat(away, ["expected goals"])
        total_xg = xg_h + xg_a

        if total_xg < 1.9:
            return None

        # Shots on Target
        sot_h = stat(home, ["shots on goal", "shots on target"])
        sot_a = stat(away, ["shots on goal", "shots on target"])
        total_sot = sot_h + sot_a

        if total_sot < 6:
            return None

        # Total Shots
        sh_h = stat(home, ["total shots"])
        sh_a = stat(away, ["total shots"])
        total_shots = sh_h + sh_a

        if total_shots < 14:
            return None

        # Dangerous Attacks
        da_h = stat(home, ["dangerous attacks"])
        da_a = stat(away, ["dangerous attacks"])
        total_da = da_h + da_a

        if total_da < 90:
            return None

        # Corners
        c_h = stat(home, ["corner kicks"])
        c_a = stat(away, ["corner kicks"])
        total_corners = c_h + c_a

        if total_corners < 8:
            return None

        # Difference Dangerous Attacks ≥ 18
        diff_da = abs(da_h - da_a)

        if diff_da < 18:
            return None

        # Momentum ≥ 70
        # formula interna professionale
        momentum = (
            total_sot * 6 +
            total_shots * 2 +
            total_xg * 15 +
            total_corners * 2 +
            diff_da * 1.2
        )

        if momentum < 70:
            return None

        # squadra dominante
        if da_h > da_a:
            focus = match["teams"]["home"]["name"]
        else:
            focus = match["teams"]["away"]["name"]

        return {
            "minute": minute,
            "score": f"{gh}-{ga}",
            "focus": focus,
            "momentum": round(momentum),
            "xg": round(total_xg, 2),
            "sot": total_sot,
            "shots": total_shots,
            "danger": total_da,
            "corners": total_corners
        }

    except:
        return None


# =====================================
# INVIO TELEGRAM
# =====================================
async def send_signal(match, info):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]

    text = (
        f"🚨 NEXT GOAL PRO SIGNAL\n\n"
        f"{home} vs {away}\n"
        f"⚽ {info['score']}\n"
        f"⏱ {info['minute']}'\n\n"
        f"🔥 Dominio: {info['focus']}\n"
        f"📈 Momentum: {info['momentum']}\n"
        f"xG: {info['xg']}\n"
        f"🎯 SOT: {info['sot']}\n"
        f"🚀 Shots: {info['shots']}\n"
        f"⚠️ Dangerous: {info['danger']}\n"
        f"🏁 Corners: {info['corners']}\n\n"
        f"💣 Probabile Prossimo Goal"
    )

    await bot.send_message(chat_id=CHAT_ID, text=text)


# =====================================
# LOOP
# =====================================
async def main():
    print("🚀 NEXT GOAL ELITE ATTIVO")

    while True:
        try:
            matches = get_matches()
            now = time.time()

            for match in matches:
                match_id = match["fixture"]["id"]

                # cooldown
                if match_id in sent_matches:
                    if now - sent_matches[match_id] < COOLDOWN:
                        continue

                info = analyze_match(match)

                if info:
                    await send_signal(match, info)
                    sent_matches[match_id] = now

        except Exception as e:
            print("ERRORE:", e)

        await asyncio.sleep(CHECK_INTERVAL)


# =====================================
# START
# =====================================
asyncio.run(main())
