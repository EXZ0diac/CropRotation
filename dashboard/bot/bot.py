"""
Simple Telegram bot (polling) that acts as a backup: queries the dashboard API for latest readings.
Requires TELEGRAM_TOKEN and ADMIN_CHAT in environment or a .env file.
"""
import os
import requests
import telegram
from telegram.ext import CommandHandler

API_URL = os.getenv('DASHBOARD_API_BASE', os.getenv('DASHBOARD_API_URL', 'http://127.0.0.1:8000'))
API_KEY = os.getenv('DASHBOARD_API_KEY', 'dev-token')
# Accept multiple env var names for the bot token for flexibility
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
ADMIN_CHAT = os.getenv('ADMIN_CHAT')

def get_latest():
    try:
        r = requests.get(API_URL + '/api/readings/latest', headers={'x-api-key':API_KEY})
        if r.status_code != 200:
            return f'Error: {r.status_code} {r.text}'
        d = r.json()
        return f"Latest:\nN={d.get('np_n')} P={d.get('np_p')} K={d.get('np_k')}\npH={d.get('ph')} EC={d.get('ec')}\nHumidity={d.get('humidity')}% Temp={d.get('temperature')}°C"
    except Exception as e:
        return f'Exception: {e}'

def start(update, context):
    update.message.reply_text('Soil Sensor bot online. Use /latest to get latest readings.')

def latest(update, context):
    update.message.reply_text(get_latest())

def history(update, context):
    try:
        r = requests.get(API_URL + '/api/readings/history?limit=20', headers={'x-api-key':API_KEY})
        if r.status_code != 200:
            update.message.reply_text(f'Error: {r.status_code}')
            return
        items = r.json()
        lines = []
        for it in items[:10]:
            lines.append(f"{it['timestamp']}: T={it['temperature']} pH={it['ph']} N={it['np_n']}")
        update.message.reply_text('\n'.join(lines) if lines else 'No history')
    except Exception as e:
        update.message.reply_text(str(e))

def main():
    if not TELEGRAM_TOKEN:
        print('TELEGRAM_TOKEN not set; bot will not start')
        return

    # The python-telegram-bot library changed to an async API in v20.
    # Try to start using the legacy Updater if available; otherwise fall back to the async ApplicationBuilder.
    try:
        # Try legacy Updater interface (synchronous)
        from telegram.ext import Updater
        updater = Updater(TELEGRAM_TOKEN)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler('start', start))
        dp.add_handler(CommandHandler('latest', latest))
        dp.add_handler(CommandHandler('history', history))

        print('Starting bot (sync Updater)...')
        updater.start_polling()
        updater.idle()
        return
    except Exception:
        pass

    # Fallback to async Application (v20+)
    try:
        from telegram.ext import ApplicationBuilder, ContextTypes

        async def start_async(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text('Soil Sensor bot online. Use /latest to get latest readings.')

        async def latest_async(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(get_latest())

        async def history_async(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                r = requests.get(API_URL + '/api/readings/history?limit=20', headers={'x-api-key':API_KEY})
                if r.status_code != 200:
                    await update.message.reply_text(f'Error: {r.status_code}')
                    return
                items = r.json()
                lines = []
                for it in items[:10]:
                    lines.append(f"{it['timestamp']}: T={it['temperature']} pH={it['ph']} N={it['np_n']}")
                await update.message.reply_text('\n'.join(lines) if lines else 'No history')
            except Exception as e:
                await update.message.reply_text(str(e))

        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler('start', start_async))
        app.add_handler(CommandHandler('latest', latest_async))
        app.add_handler(CommandHandler('history', history_async))

        print('Starting bot (async Application)...')
        app.run_polling()
    except Exception as e:
        print('Failed to start bot:', e)

if __name__ == '__main__':
    main()
