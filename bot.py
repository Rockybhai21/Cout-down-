import asyncio
import logging
import re
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store active countdowns with (chat_id, message_id) as key
active_countdowns = {}

# Fun facts and quotes
FUN_FACTS = [ 
    # Keep previous fun facts list
]

QUOTES = [
    # Keep previous quotes list
]

def parse_time_input(text):
    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    matches = re.findall(r"(\d+)(s|m|h|d|w)", text)
    return sum(int(amt) * time_units[unit] for amt, unit in matches) if matches else None

def format_time(seconds):
    # Keep previous format_time function
    pass

async def start(update: Update, context: CallbackContext):
    welcome_msg = (
        "👋 Welcome!\nUse /count [time][unit] [message]\n"
        "Example: /count 2h30m Quiz starting soon!"
    )
    await update.message.reply_text(welcome_msg)

async def count_command(update: Update, context: CallbackContext):
    try:
        args = update.message.text.split()[1:]
        time_part = "".join([x for x in args if any(c in x for c in ['s','m','h','d','w'])])
        message = " ".join([x for x in args if not any(c in x for c in ['s','m','h','d','w'])])
        
        duration = parse_time_input(time_part)
        if not duration:
            raise ValueError

        keyboard = [
            [InlineKeyboardButton("✅ Start Countdown", callback_data=f"confirm_{duration}_{message}")]
        ]
        await update.message.reply_text(
            f"⏳ Set {format_time(duration)} countdown with message:\n{message}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await update.message.reply_text("Invalid format! Use: /count 1h30m Your message here")

async def confirm_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_')
    duration = int(duration)
    
    msg = await query.message.reply_text(f"⏳ Starting countdown: {message}")
    
    # Store countdown with composite key
    key = (msg.chat.id, msg.message_id)
    active_countdowns[key] = {
        "remaining": duration,
        "paused": False,
        "message": msg,
        "custom_text": message
    }
    
    # Add control buttons
    keyboard = [
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{msg.message_id}"),
         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{msg.message_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg.message_id}")]
    ]
    await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    
    asyncio.create_task(run_countdown(key))

async def run_countdown(key):
    data = active_countdowns.get(key)
    while data and data["remaining"] > 0:
        if data["paused"]:
            await asyncio.sleep(1)
            continue
            
        await asyncio.sleep(1)
        data["remaining"] -= 1
        
        try:
            await data["message"].edit_text(
                f"⏳ {data['custom_text']}\n"
                f"Time remaining: {format_time(data['remaining'])}"
            )
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
            break

    if key in active_countdowns:
        await data["message"].edit_text(f"🎉 TIME'S UP! {data['custom_text']}")
        del active_countdowns[key]

async def handle_control(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    action, msg_id = query.data.split('_')
    msg_id = int(msg_id)
    key = (query.message.chat.id, msg_id)
    
    if key not in active_countdowns:
        return

    if action == "pause":
        active_countdowns[key]["paused"] = True
        await query.message.reply_text("⏸ Countdown paused")
    elif action == "resume":
        active_countdowns[key]["paused"] = False
        await query.message.reply_text("▶ Countdown resumed")
    elif action == "cancel":
        await query.message.reply_text("❌ Countdown cancelled")
        await active_countdowns[key]["message"].delete()
        del active_countdowns[key]

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(handle_control, pattern=r"(pause|resume|cancel)_\d+"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
