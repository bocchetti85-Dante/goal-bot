import asyncio
import os
import requests
from telegram import Bot

# === VARIABILI (Railway) ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

# === PRENDE PARTITE LIVE ===
def get_live_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {
        "x-apisports-key": API_KEY
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    return data.get("response", [])


# === TEST BOT ===
async def main():
    print("🚀 BOT AVVIATO")

    while True:
        try:
            matches = get_live_matches()
            print(f"📊 Match live trovati: {len(matches)}")

            for match in matches:
                fixture = match["fixture"]
                teams = match["teams"]
                goals = match["goals"]

                minute = fixture["status"]["elapsed"]

                home = teams["home"]["name"]
                away = teams["away"]["name"]

                home_goals = goals["home"]
                away_goals = goals["away"]

                # MESSAGGIO TEST
                message = (
                    f"🧪 TEST BOT\n"
                    f"{home} vs {away}\n"
                    f"⏱ Minuto: {minute}\n"
                    f"⚽ Score: {home_goals}-{away_goals}"
                )

                print("📤 Invio messaggio:", home, away)

                await bot.send_message(chat_id=CHAT_ID, text=message)

                # manda solo 1 partita per ciclo (per non spammare)
                break

        except Exception as e:
            print("❌ ERRORE:", e)

        await asyncio.sleep(60)  # ogni 60 secondi


if __name__ == "__main__":
    asyncio.run(main())
