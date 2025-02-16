import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}
modify_requests = {}  # Stores users modifying countdowns

# Function to parse time input
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text)
    
    total = 0
    for value, unit in matches:
        unit = unit.lower().rstrip('s')  # Handle plurals
        if unit in time_units:
            total += int(value) * time_units[unit]
    return total

# Function to format time
def format_duration(seconds: int) -> str:
    periods = [('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
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
        "Example: /count 2 minutes Quiz starts!"
    )

# Handle /count command
async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            raise ValueError
        
        input_text = ' '.join(args)
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

        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
             InlineKeyboardButton("✏ Modify", callback_data=f"modify_{update.message.chat_id}")]
        ]
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n"
            f"⚠️ {message}\n\n"
            "Confirm or modify the countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /count <time> <message>\n"
            "Example: /count 2 minutes Quiz starts!"
        )

# Handle Modify button
async def modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.split("_")[1])
    modify_requests[chat_id] = True  # Track modification request
    
    await query.message.reply_text("✏ Send the new countdown time and message in this format:\n`2 minutes New message`", parse_mode="Markdown")

# Handle new modified input
async def handle_modified_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in modify_requests:
        return  # Ignore if not modifying

    input_text = update.message.text
    time_pattern = r'(\d+\s*(?:seconds?|sec|s|minutes?|min|m|hours?|hr|h|days?|d)\s*)+'
    time_match = re.search(time_pattern, input_text, re.IGNORECASE)
    
    if not time_match:
        await update.message.reply_text("❌ Invalid time format! Please try again.")
        return
    
    time_part = time_match.group(0).strip()
    message = input_text.replace(time_part, '').strip() or "Countdown in progress..."
    duration = parse_duration(time_part)
    
    if not duration:
        await update.message.reply_text("❌ Invalid time format! Please try again.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}")]
    ]
    await update.message.reply_text(
        f"✅ New Countdown: {format_duration(duration)}\n⚠️ {message}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    del modify_requests[chat_id]  # Remove modify request

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    
    header_msg = await query.message.reply_text(
        f"📢 Countdown for:\n⚠️ <b>{message}</b>",
        parse_mode="HTML"
    )

    keyboard = [
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")]
    ]
    countdown_msg = await query.message.reply_text(
        f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await asyncio.sleep(3)
    await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)

    key = (chat_id, countdown_msg.message_id)
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'header_id': header_msg.message_id,
        'message': message
    }

    asyncio.create_task(update_countdown(key, context))

# Update countdown
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns:
        data = active_countdowns[key]
        
        if data['paused']:
            await asyncio.sleep(1)
            continue
        
        if data['remaining'] <= 0:
            break

        data['remaining'] -= 1
        
        try:
            await context.bot.edit_message_text(
                chat_id=key[0],
                message_id=key[1],
                text=f"⏲️ <b>Remaining: {format_duration(data['remaining'])}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key[0]}"),
                     InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key[0]}"),
                     InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key[0]}")]
                ])
            )
        except:
            break
        
        await asyncio.sleep(1)

    if key in active_countdowns:
        await context.bot.send_message(chat_id=key[0], text="🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
        del active_countdowns[key]

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_modified_input))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(modify_callback, pattern=r"modify_"))
    app.add_handler(CallbackQueryHandler(update_countdown, pattern=r"pause_|resume_|cancel_"))

    app.run_polling()

if __name__ == "__main__":
    main()
