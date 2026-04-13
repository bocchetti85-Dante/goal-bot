import asyncio
import os
from telegram import Bot
import time

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

async def main():
    print("BOT HEARTBEAT AVVIATO")

    counter = 0

    while True:
        try:
            counter += 1
            now = time.strftime("%H:%M:%S")

            text = (
                f"💓 HEARTBEAT BOT\n"
                f"Ciclo: {counter}\n"
                f"Ora server: {now}\n"
                f"Bot online e funzionante"
            )

            print("Invio heartbeat", counter)

            await bot.send_message(
                chat_id=CHAT_ID,
                text=text
            )

        except Exception as e:
            print("ERRORE INVIO:", repr(e))

        await asyncio.sleep(60)

asyncio.run(main())
