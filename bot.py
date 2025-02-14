import asyncio
import json
import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
STICKER_ID = "CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ"
DB_FILE = "countdowns.db"
AUTHORIZED_CHAT_IDS = json.loads(os.getenv("AUTHORIZED_CHAT_IDS", "[]"))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Database
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS countdowns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message_id INTEGER,
        user_id INTEGER,
        duration INTEGER,
        remaining INTEGER,
        paused INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Function to check if a chat is authorized
def is_authorized(chat_id):
    return chat_id in AUTHORIZED_CHAT_IDS

# Format time function
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

# Parse time input
def parse_time(time_str):
    time_units = {"hour": 3600, "minute": 60, "second": 1}
    total_seconds = 0
    parts = time_str.split()
    for i in range(0, len(parts) - 1, 2):
        try:
            num = int(parts[i])
            unit = parts[i + 1].rstrip("s")
            if unit in time_units:
                total_seconds += num * time_units[unit]
        except ValueError:
            return None
    return total_seconds if total_seconds > 0 else None

# Start command
async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not is_authorized(chat_id):
        await update.message.reply_text("❌ This chat is not authorized to use the bot.")
        return
    keyboard = [[InlineKeyboardButton("⏳ Start Countdown", callback_data="set_countdown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Click below to start a countdown:", reply_markup=reply_markup)

# Handle button clicks
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == "set_countdown":
        await query.message.edit_text("Enter the countdown duration (e.g., '2 hours 30 minutes'):")
    elif query.data.startswith("confirm_"):
        await confirm_countdown(update, context)

# Handle countdown input
async def countdown_input(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not is_authorized(chat_id):
        await update.message.reply_text("❌ This chat is not authorized to use the bot.")
        return
    
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)
    user_id = update.message.from_user.id

    if seconds is None or seconds <= 0:
        await update.message.reply_text("❌ Invalid time format! Please enter a valid duration.")
        return

    keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{user_id}_{seconds}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for <b>{format_time(seconds)}</b>?", reply_markup=reply_markup, parse_mode="HTML")

# Confirm and start countdown
async def confirm_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id, user_id, seconds = map(int, query.data.split("_")[1:])
    if not is_authorized(chat_id):
        await query.message.reply_text("❌ This chat is not authorized to use the bot.")
        return
    
    await query.answer()
    message = await query.message.reply_text(f"⏳ Countdown started for <b>{format_time(seconds)}</b>!", parse_mode="HTML")
    await context.bot.pin_chat_message(chat_id, message.message_id)

    cursor.execute("INSERT INTO countdowns (chat_id, message_id, user_id, duration, remaining, paused) VALUES (?, ?, ?, ?, ?, 0)", (chat_id, message.message_id, user_id, seconds, seconds))
    conn.commit()

    for i in range(seconds, 0, -1):
        cursor.execute("SELECT paused FROM countdowns WHERE message_id = ?", (message.message_id,))
        paused = cursor.fetchone()
        if paused and paused[0] == 1:
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"⏳ Countdown: <b>{format_time(i)}</b> remaining...", parse_mode="HTML")
        except:
            break
    await message.reply_text("🚨 <b>Time's up!</b> 🚨", parse_mode="HTML")
    cursor.execute("DELETE FROM countdowns WHERE message_id = ?", (message.message_id,))
    conn.commit()

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)

    if seconds is None or seconds <= 0:
        await update.message.reply_text("Invalid time format! Please enter a valid duration.")
        return

    chat_id = context.user_data.get("selected_chat_id")
    if not chat_id:
        await update.message.reply_text("❌ No chat selected.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_chat_countdown_{chat_id}_{seconds}"),
         InlineKeyboardButton("✏️ Modify", callback_data=f"start_countdown_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for <b>{format_time(seconds)}</b> in chat?", reply_markup=reply_markup, parse_mode="HTML")

# Confirm and start countdown for a chat
async def confirm_chat_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.split("_")[2])
    seconds = int(query.data.split("_")[3])

    message = await context.bot.send_message(chat_id, f"⏳ Countdown started for <b>{format_time(seconds)}</b>!", parse_mode="HTML")

    # Start countdown
    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"⏳ Countdown: <b>{format_time(i)}</b> remaining...", parse_mode="HTML")

            # Send and delete sticker at 60 seconds left
            if i == 60:
                sticker_msg = await message.reply_sticker(STICKER_ID)
                await asyncio.sleep(1)
                await sticker_msg.delete()

        except Exception:
            break  # Stop editing if message is deleted

    # Send alert when countdown finishes
    await context.bot.send_message(chat_id, "🚨 <b>Time's up!</b> 🚨", parse_mode="HTML")

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link_chat", link_chat_by_id))
    app.add_handler(CommandHandler("linked_chats", show_linked_chats))
    app.add_handler(CommandHandler("start_chat_countdown", start_chat_countdown))
    app.add_handler(CallbackQueryHandler(confirm_chat_countdown, pattern=r"start_countdown_\d+"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_chat_countdown, pattern=r"confirm_chat_countdown_\d+_\d+"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
