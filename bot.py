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

# Global storage using dictionary
active_countdowns = {}

def parse_duration(text: str) -> int:
    units = {
        's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
        'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
        'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
        'd': 86400, 'day': 86400, 'days': 86400
    }
    
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text)
    
    total = 0
    for value, unit in matches:
        unit = unit.lower().rstrip('s')  # Handle plurals
        if unit in units:
            total += int(value) * units[unit]
    return total

def format_duration(seconds: int) -> str:
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    return ' '.join(result) or "0 seconds"

async def start_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            raise ValueError
        
        duration_text = ' '.join(args[:-1])
        message = args[-1]
        
        duration = parse_duration(duration_text)
        if not duration:
            raise ValueError

        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}")]
        ]
        await update.message.reply_text(
            f"🚀 Set {format_duration(duration)} countdown\n📝 Message: {message}",
            reply_markup=InlineKeyboardMarkup(keyboard)
            
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /count <time> <message>\n"
            "Example: /count 2h30m 5minutes QuizTime!"
        )

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    
    # Create countdown message
    msg = await query.message.reply_text(
        f"⏳ Countdown Started!\n"
        f"📝 {message}\n"
        f"⏲️ Remaining: {format_duration(duration)}"
    )
    
    # Store countdown with composite key
    key = (chat_id, msg.message_id)
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'message': message
    }
    
    # Add control buttons
    keyboard = [
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{msg.message_id}"),
         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{msg.message_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{msg.message_id}")]
    ]
    await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Pin message after 3 seconds
    await asyncio.sleep(3)
    try:
        await context.bot.pin_chat_message(chat_id, msg.message_id)
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
    
    # Start countdown task
    asyncio.create_task(update_countdown(key))

async def update_countdown(key):
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
                text=(
                    f"⏳ Active Countdown\n"
                    f"📝 {data['message']}\n"
                    f"⏲️ Remaining: {format_duration(data['remaining'])}"
                ),
                reply_markup=InlineKeyboardMarkup([[ # Preserve buttons
                    InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key[1]}"),
                    InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key[1]}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key[1]}")
                ]])
            )
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
        
        await asyncio.sleep(1)
    
    if key in active_countdowns:
        await context.bot.edit_message_text(
            chat_id=key[0],
            message_id=key[1],
            text=f"🎉 Time's Up!\n{data['message']}"
        )
        del active_countdowns[key]

async def handle_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, message_id = query.data.split('_')
    message_id = int(message_id)
    key = (query.message.chat_id, message_id)
    
    if key not in active_countdowns:
        return
    
    if action == "pause":
        active_countdowns[key]['paused'] = True
        await query.message.reply_text("⏸ Countdown paused")
    elif action == "resume":
        active_countdowns[key]['paused'] = False
        await query.message.reply_text("▶ Countdown resumed")
    elif action == "cancel":
        await context.bot.delete_message(key[0], key[1])
        del active_countdowns[key]

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("count", start_countdown))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(handle_controls, pattern=r"(pause|resume|cancel)_\d+"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
