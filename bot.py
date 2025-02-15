import asyncio
import logging
import re
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables (Koyeb should have BOT_TOKEN set)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store active countdowns and channel data
active_countdowns = {}  # Format: {chat_id: {message: Message, remaining: int, paused: bool}}
managed_channels = {}   # Store authorized channels

# Fun facts and quotes (same as before)
# ... [Keep the FUN_FACTS and QUOTES arrays unchanged] ...

# Modified parse_time_input and format_time functions (same as before)
# ... [Keep parse_time_input and format_time functions unchanged] ...

async def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command for both users and channels"""
    if update.message.chat.type == "private":
        # Private chat welcome message
        welcome_message = (
            "👋 Welcome to the Countdown Bot!\n\n"
            "To use in channels:\n"
            "1. Add me as admin to your channel\n"
            "2. Send /setcountdown in the channel\n\n"
            f"💡 Fun Fact: {random.choice(FUN_FACTS)}"
        )
        await update.message.reply_text(welcome_message)
    else:
        # Channel setup
        channel_id = update.message.chat.id
        managed_channels[channel_id] = update.message.chat.title
        await update.message.reply_text("✅ This channel is now authorized for countdowns!")

async def set_countdown(update: Update, context: CallbackContext) -> None:
    """Handle countdown setup in channels"""
    if update.message.chat.id not in managed_channels:
        await update.message.reply_text("❌ Channel not authorized. Add bot as admin first!")
        return

    keyboard = [[InlineKeyboardButton("Set Countdown", callback_data=f"channel_set_{update.message.chat.id}")]]
    await update.message.reply_text(
        "⏰ Set channel countdown:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_callback(update: Update, context: CallbackContext) -> None:
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("channel_set_"):
        channel_id = int(query.data.split("_")[2])
        await query.message.edit_text("Send duration for channel countdown (e.g., '2 hours 30 minutes'):")
        context.user_data["channel_id"] = channel_id

async def channel_countdown_input(update: Update, context: CallbackContext) -> None:
    """Handle channel countdown input"""
    channel_id = context.user_data.get("channel_id")
    if not channel_id or channel_id not in managed_channels:
        return

    countdown_time = parse_time_input(update.message.text)
    if countdown_time:
        # Start countdown in channel
        message = await context.bot.send_message(
            channel_id,
            f"⏳ Channel countdown started for <b>{format_time(countdown_time)}</b>!",
            parse_mode="HTML"
        )
        
        # Add control buttons
        keyboard = [
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"channel_pause_{channel_id}"),
                InlineKeyboardButton("▶ Resume", callback_data=f"channel_resume_{channel_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"channel_cancel_{channel_id}"),
            ]
        ]
        await message.reply_text(
            "Control the channel countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Store countdown data
        active_countdowns[channel_id] = {
            "message": message,
            "remaining": countdown_time,
            "paused": False
        }
        asyncio.create_task(channel_countdown(channel_id))

async def channel_countdown(channel_id: int):
    """Countdown timer for channels"""
    countdown_data = active_countdowns.get(channel_id)
    if not countdown_data:
        return

    message = countdown_data["message"]
    while countdown_data["remaining"] > 0:
        if countdown_data["paused"]:
            await asyncio.sleep(1)
            continue
            
        await asyncio.sleep(1)
        countdown_data["remaining"] -= 1
        
        try:
            await message.edit_text(
                f"⏳ Channel countdown: <b>{format_time(countdown_data['remaining'])}</b> remaining...",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error updating channel countdown: {e}")
            break

    if channel_id in active_countdowns:
        await message.reply_text("🔔 <b>Channel countdown completed!</b> 🔔", parse_mode="HTML")
        del active_countdowns[channel_id]

# Modified control handlers for channels
async def channel_pause(update: Update, context: CallbackContext):
    query = update.callback_query
    channel_id = int(query.data.split("_")[2])
    if channel_id in active_countdowns:
        active_countdowns[channel_id]["paused"] = True
    await query.answer("⏸ Channel countdown paused")

async def channel_resume(update: Update, context: CallbackContext):
    query = update.callback_query
    channel_id = int(query.data.split("_")[2])
    if channel_id in active_countdowns:
        active_countdowns[channel_id]["paused"] = False
    await query.answer("▶ Channel countdown resumed")

async def channel_cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    channel_id = int(query.data.split("_")[2])
    if channel_id in active_countdowns:
        del active_countdowns[channel_id]
    await query.answer("❌ Channel countdown cancelled")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User handlers
    app.add_handler(CommandHandler("start", start))
    
    # Channel handlers
    app.add_handler(CommandHandler("setcountdown", set_countdown))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, channel_countdown_input))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"channel_set_\d+"))
    app.add_handler(CallbackQueryHandler(channel_pause, pattern=r"channel_pause_\d+"))
    app.add_handler(CallbackQueryHandler(channel_resume, pattern=r"channel_resume_\d+"))
    app.add_handler(CallbackQueryHandler(channel_cancel, pattern=r"channel_cancel_\d+"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
