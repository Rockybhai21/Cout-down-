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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /countdown <time> <message> to start a countdown. Example: /countdown 2 minutes Quiz starts!")

def parse_duration(text: str) -> int:
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    pattern = r'(\d+)\s*([smhd])'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit] for value, unit in matches)

def format_duration(seconds: int) -> str:
    return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"

async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError
        key = update.message.chat_id
        message_msg = await update.message.reply_text(f"⚠️ {message}")
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{key}_{duration}"),
                     InlineKeyboardButton("✏ Modify", callback_data=f"modify_{key}")]]
        countdown_msg = await update.message.reply_text(f"⏲️ Remaining: {format_duration(duration)}", reply_markup=InlineKeyboardMarkup(keyboard))
        active_countdowns[key] = {'duration': duration, 'paused': False, 'message_id': countdown_msg.message_id, 'message': message}
    except:
        await update.message.reply_text("❗ Invalid format! Use: /countdown <time> <message>")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action, chat_id = data[0], int(data[1])
    if action == "confirm":
        duration = int(data[2])
        active_countdowns[chat_id]['remaining'] = duration
        await query.edit_message_text(f"⏲️ Remaining: {format_duration(duration)}")
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=active_countdowns[chat_id]['message_id'])
        asyncio.create_task(update_countdown(chat_id, context))
    elif action == "modify":
        await query.edit_message_text("✏ Send a new countdown time and message.")
    elif action in ["pause", "resume", "cancel"] and chat_id in active_countdowns:
        if action == "pause":
            active_countdowns[chat_id]['paused'] = True
            await query.edit_message_text(f"⏸️ Countdown paused at {format_duration(active_countdowns[chat_id]['remaining'])}")
        elif action == "resume":
            active_countdowns[chat_id]['paused'] = False
            await query.edit_message_text(f"▶️ Countdown resumed at {format_duration(active_countdowns[chat_id]['remaining'])}")
        elif action == "cancel":
            del active_countdowns[chat_id]
            await query.edit_message_text("❌ Countdown canceled!")

async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns and active_countdowns[key]['remaining'] > 0:
        if active_countdowns[key]['paused']:
            await asyncio.sleep(1)
            continue
        active_countdowns[key]['remaining'] -= 1
        try:
            await context.bot.edit_message_text(chat_id=key, message_id=active_countdowns[key]['message_id'],
                                                text=f"⏲️ Remaining: {format_duration(active_countdowns[key]['remaining'])}",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                                                                                     InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                                                                                     InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]]))
        except:
            break
        await asyncio.sleep(1)
    if key in active_countdowns:
        await context.bot.send_message(chat_id=key, text="🎉 TIME'S UP!", parse_mode="HTML")
        del active_countdowns[key]

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"confirm_|modify_|pause_|resume_|cancel_"))
    app.run_polling()

if __name__ == "__main__":
    main()
