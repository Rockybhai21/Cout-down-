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

# Function to parse time input with spaces (e.g., "2 minutes" or "2 hours 30 minutes")
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    
    # Match patterns like "2 minutes" or "1 hour 30 minutes"
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text)
    
    total = 0
    for value, unit in matches:
        unit = unit.lower().rstrip('s')  # Handle plurals
        if unit in time_units:
            total += int(value) * time_units[unit]
    return total

# Function to format time in days, hours, minutes, seconds
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

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n\n"
        "Use /count <time> <message> to start a countdown.\n"
        "Example: /count 2 hours 30 minutes Quiz starting soon!"
    )

# Handle /count command
async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            raise ValueError
        
        # Extract time and message
        time_part = ' '.join(args[:-1]) if len(args) > 1 else args[0]
        message = ' '.join(args[-1:]) if len(args) > 1 else "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        # Add Confirm and Modify buttons
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
             InlineKeyboardButton("✏ Modify", callback_data=f"modify_{duration}_{message}")]
        ]
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n"
            f"📝 Message: {message}\n\n"
            "Confirm or modify the countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard)
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /count <time> <message>\n"
            "Example: /count 2 hours 30 minutes Quiz starting soon!"
        )

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    
    # Send the header message
    header_msg = await query.message.reply_text(
        f"📢 Countdown for:\n⚠️ <b>{message}</b>",
        parse_mode="HTML"
    )
    
    # Send the countdown message
    countdown_msg = await query.message.reply_text(
        f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{header_msg.message_id}"),
             InlineKeyboardButton("▶ Resume", callback_data=f"resume_{header_msg.message_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{header_msg.message_id}")]
        ])
    )
    
    # Store countdown with composite key
    key = (chat_id, countdown_msg.message_id)
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'header_id': header_msg.message_id,
        'message': message
    }
    
    # Pin the countdown message after 3 seconds
    await asyncio.sleep(3)
    await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)
    
    # Start countdown task
    asyncio.create_task(update_countdown(key, context))

# Handle Modify button
async def modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    
    # Prompt the user to enter a new duration and message
    await query.message.reply_text(
        "✏ Enter the new duration and message in the format:\n"
        "/count <time> <message>\n"
        f"Current duration: {format_duration(duration)}\n"
        f"Current message: {message}"
    )

# Update countdown in real-time
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
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{data['header_id']}"),
                     InlineKeyboardButton("▶ Resume", callback_data=f"resume_{data['header_id']}"),
                     InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{data['header_id']}")]
                ])
            )
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
            break  # Exit if editing fails
        
        await asyncio.sleep(1)
    
    if key in active_countdowns:
        await context.bot.send_message(
            chat_id=key[0],
            text=f"🎉 <b>TIME'S UP!</b>\n\n📢 {active_countdowns[key]['message']}",
            parse_mode="HTML"
        )
        del active_countdowns[key]

# Handle Pause, Resume, and Cancel buttons
async def handle_controls(update: Update, context: Context
