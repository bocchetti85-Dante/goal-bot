import asyncio
import os
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

async def main():
    bot = Bot(token=TOKEN)

    print("🚀 Invio messaggio test...")

    await bot.send_message(
        chat_id=CHAT_ID,
        text="🔥 TEST OK - Se vedi questo, il bot funziona!"
    )

asyncio.run(main())
