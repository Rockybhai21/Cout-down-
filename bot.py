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

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n\n"
        "Use /countdown <time> <message> to start a countdown.\n"
        "Example: /countdown 2m Quiz starts!\n\n"
        "⏲️ Supported time formats: seconds (s), minutes (m), hours (h), days (d).\n"
        "Example: 10s, 2m, 1h 30m, 1d 2h 30m."
    )

# Parse time input (e.g., "2m", "1h 30m")
def parse_duration(text: str) -> int:
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    pattern = r'(\d+)\s*([smhd])'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit] for value, unit in matches)

# Format time in minutes and seconds
def format_duration(seconds: int) -> str:
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"

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
        time_match = re.search(r'\d+\s*[smhd]', input_text, re.IGNORECASE)
        
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip()
        
        if not message:
            message = "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        # Send the header message
        header_msg = await update.message.reply_text(
            f"📢 Countdown for:\n⚠️ <b>{message}</b>",
            parse_mode="HTML"
        )
        
        # Send the countdown message with buttons
        keyboard = [
            [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{update.message.chat_id}"),
             InlineKeyboardButton("▶ Resume", callback_data=f"resume_{update.message.chat_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{update.message.chat_id}")]
        ]
        countdown_msg = await update.message.reply_text(
            f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Pin countdown after 3 seconds
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(update.message.chat_id, countdown_msg.message_id)
        
        # Store countdown
        key = update.message.chat_id
        active_countdowns[key] = {
            'remaining': duration,
            'paused': False,
            'header_id': header_msg.message_id,
            'countdown_id': countdown_msg.message_id,
            'message': message
        }
        
        # Start countdown task
        asyncio.create_task(update_countdown(key, context))
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /countdown <time> <message>\n"
            "Example: /countdown 2m Quiz starts!"
        )

# Update countdown in real-time
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns and active_countdowns[key]['remaining'] > 0:
        if active_countdowns[key]['paused']:
            await asyncio.sleep(1)
            continue
        
        active_countdowns[key]['remaining'] -= 1
        
        try:
            keyboard = [
                [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                 InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
            ]
            await context.bot.edit_message_text(
                chat_id=key,
                message_id=active_countdowns[key]['countdown_id'],
                text=f"⏲️ <b>Remaining: {format_duration(active_countdowns[key]['remaining'])}</b>",
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

# Handle button callbacks (Pause, Resume, Cancel)
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
        await query.edit_message_text(
            text=f"⏸️ <b>Countdown paused at:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
            parse_mode="HTML"
        )
    elif action == "resume":
        active_countdowns[key]['paused'] = False
        await query.edit_message_text(
            text=f"▶️ <b>Countdown resumed at:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
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
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
