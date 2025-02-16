import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

def parse_duration(text: str) -> int:
    time_units = {
        's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
        'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
        'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
        'd': 86400, 'day': 86400, 'days': 86400
    }
    pattern = r"(\d+)\s*([a-zA-Z]+)"
    matches = re.findall(pattern, text)
    total = 0
    for value, unit in matches:
        unit = unit.lower().rstrip('s')
        if unit in time_units:
            total += int(value) * time_units[unit]
    return total

def format_duration(seconds: int) -> str:
    periods = [('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    return ' '.join(result) or "0 seconds"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌹 Welcome to the Countdown Bot!\n\nUse /count <time> <message> to start a countdown.")

async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            raise ValueError
        
        input_text = ' '.join(args)
        time_pattern = r"(\d+\s*(?:seconds?|sec|s|minutes?|min|m|hours?|hr|h|days?|d)\s*)+"
        time_match = re.search(time_pattern, input_text, re.IGNORECASE)
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip() or "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}")]]
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n⚠️ {message}\nConfirm or modify:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.message.reply_text("❗ Invalid format! Use: /count <time> <message>")

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id

    countdown_msg = await query.message.reply_text(f"⏲️ <b>Remaining: {format_duration(duration)}</b>", parse_mode="HTML")
    
    key = (chat_id, countdown_msg.message_id)
    active_countdowns[key] = {'remaining': duration, 'paused': False, 'message': message}
    asyncio.create_task(update_countdown(key, context))

async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while True:
        data = active_countdowns.get(key)
        if not data or data['remaining'] <= 0:
            break
        
        if data['paused']:
            await asyncio.sleep(1)
            continue
        
        data['remaining'] -= 1
        try:
            await context.bot.edit_message_text(
                chat_id=key[0],
                message_id=key[1],
                text=f"⏲️ <b>Remaining: {format_duration(data['remaining'])}</b>",
                parse_mode="HTML"
            )
        except Exception:
            break
        
        await asyncio.sleep(1)
    
    if key in active_countdowns:
        await context.bot.send_message(chat_id=key[0], text="🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
        del active_countdowns[key]

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, chat_id, message_id = query.data.split('_', 2)
    key = (int(chat_id), int(message_id))
    
    if key not in active_countdowns:
        await query.edit_message_text(text="❌ Countdown not found!")
        return
    
    if action == "pause":
        active_countdowns[key]['paused'] = True
    elif action == "resume":
        active_countdowns[key]['paused'] = False
    elif action == "cancel":
        del active_countdowns[key]
        await query.edit_message_text(text="❌ <b>Countdown canceled!</b>", parse_mode="HTML")
        return
    
    await query.edit_message_text(
        text=f"{'⏸ Paused' if action == 'pause' else '▶️ Resumed'}: {format_duration(active_countdowns[key]['remaining'])}",
        parse_mode="HTML"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    app.run_polling()

if __name__ == "__main__":
    main()
