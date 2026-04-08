import asyncio
import os
import requests
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

def get_live_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_KEY}

    response = requests.get(url, headers=headers)
    data = response.json()

    return data.get("response", [])


async def main():
    print("🚀 BOT AVVIATO")

    while True:
        try:
            matches = get_live_matches()

            print(f"📊 Match live: {len(matches)}")

            # 👉 SE NON CI SONO PARTITE
            if not matches:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text="⚠️ Nessuna partita live trovata"
                )

            else:
                match = matches[0]

                fixture = match["fixture"]
                teams = match["teams"]
                goals = match["goals"]

                minute = fixture["status"]["elapsed"]

                home = teams["home"]["name"]
                away = teams["away"]["name"]

                home_goals = goals["home"]
                away_goals = goals["away"]

                message = (
                    f"🧪 TEST LIVE\n"
                    f"{home} vs {away}\n"
                    f"⏱ {minute}'\n"
                    f"⚽ {home_goals}-{away_goals}"
                )

                print("📤 Invio match test")

                await bot.send_message(chat_id=CHAT_ID, text=message)

        except Exception as e:
            print("❌ ERRORE:", e)

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
