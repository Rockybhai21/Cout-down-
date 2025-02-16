import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ChatType
from dotenv import load_dotenv

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Function to parse time input (e.g., "2 minutes", "1h 30m")
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text)
    total = sum(int(value) * time_units.get(unit.lower().rstrip('s'), 0) for value, unit in matches)
    return total

# Format duration in a readable format
def format_duration(seconds: int) -> str:
    periods = [('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
    result = [f"{value} {name}{'s' if value != 1 else ''}" for name, secs in periods if (value := seconds // secs) and (seconds := seconds % secs)]
    return ' '.join(result) or "0 seconds"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 Welcome! Use /count <time> <message> to start a countdown.")

# /count command
async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Invalid format! Use: /count <time> <message>")
        return
    input_text = ' '.join(context.args)
    time_match = re.search(r'(\d+\s*(?:seconds?|sec|s|minutes?|min|m|hours?|hr|h|days?|d)\s*)+', input_text, re.IGNORECASE)
    if not time_match:
        await update.message.reply_text("❗ Invalid time format! Example: /count 2 minutes Event starts!")
        return
    time_part, message = time_match.group(0).strip(), input_text.replace(time_match.group(0), '').strip() or "Countdown in progress..."
    duration = parse_duration(time_part)
    if not duration:
        await update.message.reply_text("❗ Invalid duration!")
        return
    keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"), InlineKeyboardButton("✏ Modify", callback_data="modify")]]
    await update.message.reply_text(f"⏳ Set {format_duration(duration)} countdown\n⚠️ {message}\nConfirm or modify:", reply_markup=InlineKeyboardMarkup(keyboard))

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    header_msg = await query.message.reply_text(f"📢 Countdown for:\n⚠️ <b>{message}</b>", parse_mode="HTML")
    keyboard = [[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}_{query.message.message_id}"), InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}_{query.message.message_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}_{query.message.message_id}")]]
    countdown_msg = await query.message.reply_text(f"⏲️ <b>Remaining: {format_duration(duration)}</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    await asyncio.sleep(3)
    await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)
    active_countdowns[(chat_id, countdown_msg.message_id)] = {'remaining': duration, 'paused': False, 'header_id': header_msg.message_id, 'message': message}
    asyncio.create_task(update_countdown((chat_id, countdown_msg.message_id), context))

# Update countdown
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns and active_countdowns[key]['remaining'] > 0:
        if active_countdowns[key]['paused']:
            await asyncio.sleep(1)
            continue
        active_countdowns[key]['remaining'] -= 1
        try:
            keyboard = [[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key[0]}_{key[1]}"), InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key[0]}_{key[1]}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key[0]}_{key[1]}")]]
            await context.bot.edit_message_text(chat_id=key[0], message_id=key[1], text=f"⏲️ <b>Remaining: {format_duration(active_countdowns[key]['remaining'])}</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            break
        await asyncio.sleep(1)
    if key in active_countdowns:
        await context.bot.send_message(chat_id=key[0], text="🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
        del active_countdowns[key]

# Handle Pause, Resume, Cancel
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
    await query.edit_message_text(text=f"{action.capitalize()}d!", parse_mode="HTML")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    app.run_polling()

if __name__ == "__main__":
    main()
