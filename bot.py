import os
import asyncio
from telegram import Update
from flask import Flask
from threading import Thread
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes
# from checker import get_latest_boost, get_latest_tokens, register, get_trending
from check import get_latest_tokens, get_latest_boost, get_trending, register
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Telegram bot is running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def start_flask():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()



async def bot():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(256).build()
    # app.add_handler(CommandHandler("register", register))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & ~filters.COMMAND, register))
    # app.add_handler(MessageHandler(filters.ALL, handle_forward))
    start_flask()

    token_checker = asyncio.create_task(run_token_checker(app))
    async with app:
        await app.start()
        await app.updater.start_polling()
        print("Bot is pooling...")

        await asyncio.Event().wait()
        try:
            await asyncio.Event().wait()
        finally:
            token_checker.cancel()
            try:
                await token_checker
            except asyncio.CancelledError:
                pass


async def run_token_checker(app):
    while True:
        try:
            from telegram.ext import CallbackContext
            from telegram import Update
            context = CallbackContext(app)
            update = Update(app)
            await get_latest_tokens(update, context)
            await asyncio.sleep(15)
            await get_latest_boost(context)
            await asyncio.sleep(15)
            await get_trending(update, context)
        except Exception as e:
            print(f"Error in checker: {e}")
        await asyncio.sleep(60) 



    
async def main():
    try:
    # Run both bots concurrently
        await asyncio.gather(
        bot()
        )
    except KeyboardInterrupt:
        print("\nShutting down bots...")

if __name__ == "__main__":
    asyncio.run(main())