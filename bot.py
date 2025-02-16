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

# Function to parse time input (e.g., "2 minutes" or "2h 30m")
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    
    # Match patterns like "2 minutes" or "1h 30m"
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

# Handle /countdown command
async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the command is used in a group or supergroup
    if update.message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return
    
    try:
        args = context.args
        if not args:
            raise ValueError
        
        # Extract time and message
        input_text = ' '.join(args)
        
        # Match time formats (e.g., "2 minutes", "10s", "1h 30m")
        time_pattern = r'(\d+\s*(?:seconds?|sec|s|minutes?|min|m|hours?|hr|h|days?|d)\s*)+'
        time_match = re.search(time_pattern, input_text, re.IGNORECASE)
        
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip()
        
        if not message:
            message = "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        # Send the countdown message with Pause, Resume, and Cancel buttons
        keyboard = [
            [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{update.message.chat_id}"),
             InlineKeyboardButton("▶ Resume", callback_data=f"resume_{update.message.chat_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{update.message.chat_id}")]
        ]
        countdown_msg = await update.message.reply_text(
            f"⏳ Countdown started for {format_duration(duration)}!\n"
            f"⚠️ {message}\n\n"
            f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        
        # Store countdown
        key = update.message.chat_id
        active_countdowns[key] = {
            'remaining': duration,
            'paused': False,
            'message_id': countdown_msg.message_id,
            'message': message
        }
        
        # Start countdown task
        asyncio.create_task(update_countdown(key, context))
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /countdown <time> <message>\n"
            "Example: /countdown 2 minutes Quiz starts!"
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
            keyboard = [
                [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                 InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
            ]
            await context.bot.edit_message_text(
                chat_id=key,
                message_id=data['message_id'],
                text=f"⏳ Countdown for: {data['message']}\n"
                     f"⏲️ <b>Remaining: {format_duration(data['remaining'])}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
            break  # Exit if editing fails
        
        await asyncio.sleep(1)
    
    if key in active_countdowns:
        await context.bot.send_message(
            chat_id=key,
            text="🎉 <b>TIME'S UP!</b>",
            parse_mode="HTML"
        )
        del active_countdowns[key]

# Handle Pause, Resume, and Cancel buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, chat_id = query.data.split('_', 1)
    key = int(chat_id)
    
    if key not in active_countdowns:
        await query.edit_message_text(text="❌ Countdown not found!")
        return
    
    if action == "pause":
        active_countdowns[key]['paused'] = True
        await query.edit_message_text(
            text=f"⏸️ <b>Countdown paused:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
            parse_mode="HTML"
        )
    elif action == "resume":
        active_countdowns[key]['paused'] = False
        await query.edit_message_text(
            text=f"▶️ <b>Countdown resumed:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
            parse_mode="HTML"
        )
    elif action == "cancel":
        del active_countdowns[key]
        await query.edit_message_text(
            text="❌ <b>Countdown canceled!</b>",
            parse_mode="HTML"
        )

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    
    # Ignore all other messages
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, lambda update, context: None))
    
    app.run_polling()

if __name__ == "__main__":
    main()
