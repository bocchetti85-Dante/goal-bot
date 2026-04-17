import asyncio
import os
import requests
from telegram import Bot
import time

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

sent_matches = {}
COOLDOWN = 900   # 15 minuti


# =========================
# LIVE MATCHES
# =========================
def get_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("response", [])
    except:
        return []


# =========================
# SAFE VALUE
# =========================
def val(stats, names):
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


# =========================
# CHECK MATCH
# =========================
def check_match(match):
    try:
        fixture = match["fixture"]
        status = fixture["status"]

        match_id = fixture["id"]
        minute = status["elapsed"]

        if minute is None:
            return None

        # -------------------------
        # FINESTRA ORARIA PRO
        # 70-89 normali
        # 90+ solo se recupero >=6
        # -------------------------
        if 70 <= minute <= 89:
            pass

        elif minute >= 90:
            extra = status.get("extra")

            if extra is None or extra < 6:
                return None
        else:
            return None

        # cooldown
        now = time.time()

        if match_id in sent_matches:
            if now - sent_matches[match_id] < COOLDOWN:
                return None

        # risultato
        gh = match["goals"]["home"]
        ga = match["goals"]["away"]

        if gh is None or ga is None:
            return None

        # partita ancora viva
        if abs(gh - ga) > 2:
            return None

        home_name = match["teams"]["home"]["name"]
        away_name = match["teams"]["away"]["name"]

        stats = match.get("statistics")

        # Se stats mancanti ma recupero alto
        if not stats or len(stats) < 2:
            if minute >= 90:
                return "FINAL PUSH"
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        # shots on target
        sot_h = val(home, ["shots on goal", "shots on target"])
        sot_a = val(away, ["shots on goal", "shots on target"])

        # dangerous attacks
        dang_h = val(home, ["dangerous attacks"])
        dang_a = val(away, ["dangerous attacks"])

        total_sot = sot_h + sot_a

        # minimo pressione
        if total_sot < 4:
            return None

        # dominio casa
        if dang_h > dang_a + 5:
            return home_name

        # dominio ospite
        if dang_a > dang_h + 5:
            return away_name

        # partita apertissima finale
        if minute >= 82 and total_sot >= 6:
            return "MATCH OPEN"

    except:
        return None

    return None


# =========================
# BOT LOOP
# =========================
async def main():
    print("🚀 BOT PRO 70-90 ATTIVO")

    while True:
        try:
            matches = get_matches()
            print("LIVE MATCH:", len(matches))

            for match in matches:
                result = check_match(match)

                if not result:
                    continue

                match_id = match["fixture"]["id"]

                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]

                minute = match["fixture"]["status"]["elapsed"]
                extra = match["fixture"]["status"].get("extra")

                gh = match["goals"]["home"]
                ga = match["goals"]["away"]

                minute_text = f"{minute}'"

                if minute >= 90 and extra:
                    minute_text = f"{minute}+{extra}'"

                text = (
                    f"🚨 ENTRY PRO\n"
                    f"{home} vs {away}\n"
                    f"⚽ {gh}-{ga}\n"
                    f"⏱ {minute_text}\n"
                    f"🔥 Focus: {result}\n"
                    f"🎯 Possibile prossimo goal"
                )

                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=text
                )

                sent_matches[match_id] = time.time()

        except Exception as e:
            print("ERRORE:", e)

        await asyncio.sleep(30)


# =========================
# START
# =========================
asyncio.run(main())
