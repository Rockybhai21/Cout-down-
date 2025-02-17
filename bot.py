import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n\n"
        "Use /countdown <time> <message> to start a countdown.\n"
        "Example: /countdown 2m Quiz starts!"
    )

# Parse time input (e.g., "2m", "1h 30m", "2 minutes")
def parse_duration(text: str) -> int:
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    pattern = r'(\d+)\s*([smhd])'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit] for value, unit in matches)

# Format time for display
def format_duration(seconds: int) -> str:
    return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"

# Handle /countdown command
async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type in ["group", "supergroup"] and not update.message.text.startswith("/countdown"):
        return  # Ignore non-command messages in groups
    
    try:
        args = context.args
        if not args:
            raise ValueError
        input_text = ' '.join(args)
        time_match = re.search(r'\d+\s*[smhd]', input_text, re.IGNORECASE)
        if not time_match:
            raise ValueError
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip() or "Countdown in progress..."
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
                     InlineKeyboardButton("✏ Modify", callback_data="modify")]]
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n⚠️ {message}\n\nConfirm or modify:",
            reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await update.message.reply_text("❗ Invalid format! Use: /countdown <time> <message>")

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    header_msg = await query.message.reply_text(f"📢 Countdown for: <b>{message}</b>", parse_mode="HTML")
    keyboard = [[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
                 InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")]]
    countdown_msg = await query.message.reply_text(
        f"⏲️ <b>Remaining: {format_duration(duration)}</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    if query.message.chat.type in ["group", "supergroup"]:
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)
    active_countdowns[chat_id] = {
        'remaining': duration, 'paused': False,
        'header_id': header_msg.message_id,
        'countdown_id': countdown_msg.message_id,
        'message': message,
        'task': asyncio.create_task(update_countdown(chat_id, context))
    }

# Update countdown in real-time
async def update_countdown(chat_id, context: ContextTypes.DEFAULT_TYPE):
    while chat_id in active_countdowns and active_countdowns[chat_id]['remaining'] > 0:
        if active_countdowns[chat_id]['paused']:
            await asyncio.sleep(1)
            continue
        active_countdowns[chat_id]['remaining'] -= 1
        try:
            keyboard = [[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
                         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
                         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")]]
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=active_countdowns[chat_id]['countdown_id'],
                text=f"⏲️ <b>Remaining: {format_duration(active_countdowns[chat_id]['remaining'])}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            break  # Exit if editing fails
        await asyncio.sleep(1)
    if chat_id in active_countdowns:
        await context.bot.send_message(chat_id=chat_id, text="🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
        del active_countdowns[chat_id]

# Handle Pause, Resume, and Cancel buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, chat_id = query.data.split('_')
    chat_id = int(chat_id)
    if chat_id not in active_countdowns:
        await query.edit_message_text(text="❌ Countdown not found!")
        return
    if action == "pause":
        active_countdowns[chat_id]['paused'] = True
    elif action == "resume":
        active_countdowns[chat_id]['paused'] = False
    elif action == "cancel":
        active_countdowns[chat_id]['task'].cancel()
        del active_countdowns[chat_id]
    await query.edit_message_text(text=f"{action.capitalize()}d countdown at {format_duration(active_countdowns[chat_id]['remaining'])}")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    app.run_polling()

if __name__ == "__main__":
    main()
