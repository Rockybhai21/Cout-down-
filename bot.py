import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ChatType
from dotenv import load_dotenv
from flask import Flask, request

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Set this in your environment variables
PORT = int(os.getenv("PORT", 5000))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for webhook
app = Flask(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n\n"
        "Use /countdown <time> <message> to start a countdown.\n"
        "Example: /countdown 2m Quiz starts!\n\n"
        "⏲️ Supported time formats:\n"
        "- Seconds: `10s`, `10 seconds`\n"
        "- Minutes: `2m`, `2 minutes`\n"
        "- Hours: `1h`, `1 hour`\n"
        "- Days: `1d`, `1 day`\n"
        "- Combined: `1h 30m`, `1d 2h 30m`\n\n"
        "📢 The bot works in both private messages and groups.\n"
        "✅ Use /countdown to get started!"
    )

# Parse time input

def parse_duration(text: str) -> int:
    time_units = {
        's': 1, 'm': 60, 'h': 3600, 'd': 86400
    }
    pattern = r'(\d+)\s*([smhd])'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit] for value, unit in matches)

# Format time display
def format_duration(seconds: int) -> str:
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"

# Countdown command
async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return
    try:
        args = context.args
        if not args:
            raise ValueError
        
        input_text = ' '.join(args)
        time_match = re.search(r'\d+\s*[smhd]', input_text, re.IGNORECASE)
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip()
        if not message:
            message = "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError
        
        key = (update.message.chat_id, update.message.message_id)
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
                     InlineKeyboardButton("✏ Modify", callback_data="modify")]]
        
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n⚠️ {message}\n\nConfirm or modify the countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await update.message.reply_text("❗ Invalid format! Use: /countdown <time> <message>")

# Confirm button handler
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    
    header_msg = await query.message.reply_text(f"📢 Countdown for:\n⚠️ <b>{message}</b>", parse_mode="HTML")
    
    countdown_msg = await query.message.reply_text(f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
                                                   parse_mode="HTML")
    
    if query.message.chat.type in ["group", "supergroup"]:
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)
    
    key = (chat_id, countdown_msg.message_id)
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'countdown_id': countdown_msg.message_id,
        'task': asyncio.create_task(update_countdown(key, context))
    }

# Update countdown
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns and active_countdowns[key]['remaining'] > 0:
        if active_countdowns[key]['paused']:
            await asyncio.sleep(1)
            continue
        
        active_countdowns[key]['remaining'] -= 1
        try:
            await context.bot.edit_message_text(
                chat_id=key[0],
                message_id=key[1],
                text=f"⏲️ <b>Remaining: {format_duration(active_countdowns[key]['remaining'])}</b>",
                parse_mode="HTML"
            )
        except:
            break
        
        await asyncio.sleep(1)
    
    if key in active_countdowns:
        await context.bot.send_message(chat_id=key[0], text="🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
        del active_countdowns[key]

# Webhook setup
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), app.bot)
    app.update_queue.put(update)
    return "OK"

def main():
    app.bot = Application.builder().token(BOT_TOKEN).build()
    app.bot.add_handler(CommandHandler("start", start_command))
    app.bot.add_handler(CommandHandler("countdown", countdown_command))
    app.bot.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.bot.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
