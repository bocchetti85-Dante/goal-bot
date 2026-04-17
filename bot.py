import asyncio
import os
import requests
import time
from telegram import Bot

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

# =========================
# MEMORY
# =========================
signal_memory = {}
# struttura:
# match_id: {
#   "start": timestamp,
#   "last": timestamp,
#   "count": int,
#   "last_push": bool,
#   "score": "1-0"
# }

# =========================
# SETTINGS
# =========================
CHECK_INTERVAL = 30
REMINDER_EVERY = 60       # ogni minuto
MAX_REMINDERS = 5
COOLDOWN_NEW = 600        # dopo chiusura segnale


# =========================
# API LIVE MATCHES
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
# READ STATS
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
# MATCH STILL VALID?
# =========================
def analyze_match(match):
    try:
        fixture = match["fixture"]
        status = fixture["status"]

        minute = status["elapsed"]
        extra = status.get("extra")

        if minute is None:
            return None

        # Finestra tempo:
        # 70-89 normale
        # 90+ solo con recupero >=6
        if 70 <= minute <= 89:
            pass
        elif minute >= 90:
            if extra is None or extra < 6:
                return None
        else:
            return None

        gh = match["goals"]["home"]
        ga = match["goals"]["away"]

        if gh is None or ga is None:
            return None

        # no partite morte
        if abs(gh - ga) > 2:
            return None

        home_name = match["teams"]["home"]["name"]
        away_name = match["teams"]["away"]["name"]

        stats = match.get("statistics")

        if not stats or len(stats) < 2:
            # senza stats finale vivo
            if minute >= 85:
                return {
                    "minute": minute,
                    "extra": extra,
                    "focus": "FINAL PUSH",
                    "score": f"{gh}-{ga}"
                }
            return None

        home = stats[0]["statistics"]
        away = stats[1]["statistics"]

        sot_h = val(home, ["shots on goal", "shots on target"])
        sot_a = val(away, ["shots on goal", "shots on target"])

        dang_h = val(home, ["dangerous attacks"])
        dang_a = val(away, ["dangerous attacks"])

        total_sot = sot_h + sot_a

        # pressione minima
        if total_sot < 4:
            return None

        # dominio
        if dang_h > dang_a + 5:
            focus = home_name
        elif dang_a > dang_h + 5:
            focus = away_name
        elif minute >= 82 and total_sot >= 6:
            focus = "MATCH OPEN"
        else:
            return None

        return {
            "minute": minute,
            "extra": extra,
            "focus": focus,
            "score": f"{gh}-{ga}"
        }

    except:
        return None


# =========================
# FORMAT MINUTE
# =========================
def minute_text(minute, extra):
    if minute >= 90 and extra:
        return f"{minute}+{extra}'"
    return f"{minute}'"


# =========================
# SEND MESSAGE
# =========================
async def send_alert(kind, match, info):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    gh = match["goals"]["home"]
    ga = match["goals"]["away"]

    mt = minute_text(info["minute"], info["extra"])

    if kind == "ENTRY":
        text = (
            f"🚨 ENTRY MOMENTUM\n"
            f"{home} vs {away}\n"
            f"⚽ {gh}-{ga}\n"
            f"⏱ {mt}\n"
            f"🔥 Focus: {info['focus']}\n"
            f"🎯 Pressione alta"
        )

    elif kind == "REMINDER":
        text = (
            f"🔥 STILL LIVE\n"
            f"{home} vs {away}\n"
            f"⚽ {gh}-{ga}\n"
            f"⏱ {mt}\n"
            f"📈 Pressione continua"
        )

    else:  # LAST PUSH
        text = (
            f"💣 LAST PUSH\n"
            f"{home} vs {away}\n"
            f"⚽ {gh}-{ga}\n"
            f"⏱ {mt}\n"
            f"🔥 Finale acceso"
        )

    await bot.send_message(chat_id=CHAT_ID, text=text)


# =========================
# MAIN LOOP
# =========================
async def main():
    print("🚀 BOT V3 MOMENTUM ATTIVO")

    while True:
        try:
            matches = get_matches()
            now = time.time()

            for match in matches:
                match_id = match["fixture"]["id"]

                info = analyze_match(match)

                # se non più valida cancella memoria
                if not info:
                    if match_id in signal_memory:
                        del signal_memory[match_id]
                    continue

                # nuova entry
                if match_id not in signal_memory:
                    await send_alert("ENTRY", match, info)

                    signal_memory[match_id] = {
                        "start": now,
                        "last": now,
                        "count": 0,
                        "last_push": False,
                        "score": info["score"]
                    }
                    continue

                mem = signal_memory[match_id]

                # se cambia punteggio resetta
                if mem["score"] != info["score"]:
                    del signal_memory[match_id]
                    continue

                # reminder ogni minuto max 5
                if (
                    mem["count"] < MAX_REMINDERS
                    and now - mem["last"] >= REMINDER_EVERY
                ):
                    await send_alert("REMINDER", match, info)
                    mem["last"] = now
                    mem["count"] += 1

                # last push 85+
                if info["minute"] >= 85 and not mem["last_push"]:
                    await send_alert("LAST PUSH", match, info)
                    mem["last_push"] = True

        except Exception as e:
            print("ERRORE:", e)

        await asyncio.sleep(CHECK_INTERVAL)


# =========================
# START
# =========================
asyncio.run(main())
