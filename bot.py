import asyncio
import logging
import re
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
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

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store active countdowns and authorized channels
authorized_channels = set()
active_countdowns = {}
pinned_messages = {}

# Fun facts and quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was a woman named Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
    "Here's a fact: The first text message ever sent was 'Merry Christmas' in 1992. 📱",
]

QUOTES = [
    "Time is what we want most, but what we use worst. – William Penn ⏳",
    "The future depends on what you do today. – Mahatma Gandhi 🌟",
]

# Parse time input
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip("s")]
    return total_seconds if total_seconds > 0 else None

# Format time
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"<b>{days}d {hours}h {minutes}m {seconds}s</b>" if days else f"<b>{hours}h {minutes}m {seconds}s</b>" if hours else f"<b>{minutes}m {seconds}s</b>" if minutes else f"<b>{seconds}s</b>"

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "👋 Welcome to the Countdown Bot!\n\n"
        "I can help you set countdowns in PMs, groups, and channels.\n\n"
        "To set a countdown, send me the duration (e.g., '2 hours 30 minutes').\n\n"
        f"💡 Fun Fact: {random.choice(FUN_FACTS)}\n\n"
        f"💛 Quote of the Day: {random.choice(QUOTES)}"
    )
    await update.message.reply_text(welcome_message)

# Add authorized channel
async def add_channel(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add_channel <channel_id>")
        return
    channel_id = context.args[0]
    chat_member = await context.bot.get_chat_member(channel_id, update.message.from_user.id)
    if chat_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        await update.message.reply_text("Only admins can add channels.")
        return
    authorized_channels.add(channel_id)
    await update.message.reply_text(f"✅ Channel {channel_id} authorized for countdowns.")

# Handle countdown input
async def countdown_input(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)

    if countdown_time:
        context.user_data["countdown_time"] = countdown_time  # ✅ Store countdown time
        context.user_data["custom_message"] = None  # ✅ Reset custom message
        
        # Ask user if they want to add a custom message
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}")],
            [InlineKeyboardButton("💬 Add Custom Message", callback_data="set_message")],
            [InlineKeyboardButton("✏ Modify Time", callback_data="modify_time")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⏳ Countdown set for {format_time(countdown_time)}\nDo you want to confirm or add a custom message?",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Invalid time format. Please enter a valid duration.")

# Handle custom message input
async def set_custom_message(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    chat_id = update.message.chat.id

    # ✅ Make sure countdown time is stored before accepting custom message
    if "countdown_time" not in user_data:
        await update.message.reply_text("❌ No countdown time found. Please enter a time first.")
        return

    user_data["custom_message"] = update.message.text  # ✅ Store custom message

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{user_data['countdown_time']}")],
        [InlineKeyboardButton("✏ Modify", callback_data="modify_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⏳ Countdown: {format_time(user_data['countdown_time'])}\n📢 Message: <b>{user_data['custom_message']}</b>\n\nConfirm to start?",
        parse_mode="HTML",
        reply_markup=reply_markup
    )


# Confirm countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id, countdown_time = map(int, query.data.split("_")[1:])
    
    custom_message = context.user_data.get("custom_message", "⏳ Countdown started!")

    message = await query.message.reply_text(f"📢 <b>{custom_message}</b>\n⏳ Time: {format_time(countdown_time)}", parse_mode="HTML")

    # Add control buttons
    keyboard = [
        [
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
            InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("Control the countdown:", reply_markup=reply_markup)

    # Store countdown
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}

    # Delay pinning
    await asyncio.sleep(5)
    if chat_id in pinned_messages:
        await context.bot.unpin_chat_message(chat_id, pinned_messages[chat_id])
    pinned_messages[chat_id] = message.message_id
    await context.bot.pin_chat_message(chat_id, message.message_id)

    asyncio.create_task(countdown(chat_id))

# Countdown function
async def countdown(chat_id):
    countdown_data = active_countdowns.get(chat_id)
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
            await message.edit_text(f"⏳ {format_time(countdown_data['remaining'])}", parse_mode="HTML")
        except Exception:
            break
    del active_countdowns[chat_id]

# Pause, Resume, Cancel Handlers
async def pause_countdown(update: Update, context: CallbackContext): await update.callback_query.answer("⏸ Countdown paused")
async def resume_countdown(update: Update, context: CallbackContext): await update.callback_query.answer("▶ Countdown resumed")
async def cancel_countdown(update: Update, context: CallbackContext): await update.callback_query.answer("❌ Countdown cancelled")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_custom_message))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+"))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()
