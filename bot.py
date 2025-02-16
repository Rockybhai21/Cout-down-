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
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError
        key = update.message.chat_id
        countdown_msg = await update.message.reply_text(f"⏳ Countdown for\n⚠️ {message}")
        time_msg = await update.message.reply_text(f"⏲️ Remaining: {format_duration(duration)}")
        keyboard = [[InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                     InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                     InlineKeyboardButton("✏ Modify", callback_data=f"modify_{key}"),
                     InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]]
        await context.bot.edit_message_reply_markup(chat_id=key, message_id=time_msg.message_id, reply_markup=InlineKeyboardMarkup(keyboard))
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id=key, message_id=time_msg.message_id)
        active_countdowns[key] = {'remaining': duration, 'paused': False, 'message_id': time_msg.message_id, 'message': message}
        asyncio.create_task(update_countdown(key, context))
    except:
        await update.message.reply_text("❗ Invalid format! Use: /countdown <time> <message>")

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
                                                                                     InlineKeyboardButton("✏ Modify", callback_data=f"modify_{key}"),
                                                                                     InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]]))
        except:
            break
        await asyncio.sleep(1)
    if key in active_countdowns:
        await context.bot.send_message(chat_id=key, text="🎉 TIME'S UP!", parse_mode="HTML")
        del active_countdowns[key]

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, chat_id = query.data.split('_')
    key = int(chat_id)
    if key not in active_countdowns:
        await query.edit_message_text(text="❌ Countdown not found!")
        return
    if action == "pause":
        active_countdowns[key]['paused'] = True
        await query.edit_message_text(text=f"⏸️ Countdown paused at {format_duration(active_countdowns[key]['remaining'])}")
    elif action == "resume":
        active_countdowns[key]['paused'] = False
        await query.edit_message_text(text=f"▶️ Countdown resumed at {format_duration(active_countdowns[key]['remaining'])}")
    elif action == "modify":
        await query.edit_message_text(text="✏ Send new countdown time and message in format: <time> <message>")
        active_countdowns[key]['modifying'] = True
    elif action == "cancel":
        del active_countdowns[key]
        await query.edit_message_text(text="❌ Countdown canceled!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|modify_|cancel_"))
    app.run_polling()

if __name__ == "__main__":
    main()
