import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

TOKEN = "7207793925:AAFME_OkdkEMMcFd9PI7cuoP_ahAG9OHg7U"
STICKER_ID = "CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ"

# Store countdowns and channels
user_time = {}
active_countdowns = {}
managed_channels = {}

# Format time function
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

# Start command
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("⏳ Set Countdown", callback_data="set_countdown")],
                [InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

# Handle button presses
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "set_countdown":
        await query.message.edit_text("Enter the countdown duration (e.g., '2 hours 30 minutes'):")
    
    elif query.data == "manage_channels":
        if managed_channels:
            buttons = [[InlineKeyboardButton(name, callback_data=f"channel_{chat_id}")]
                       for chat_id, name in managed_channels.items()]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text("📢 Select a channel to manage:", reply_markup=reply_markup)
        else:
            await query.message.edit_text("No channels added. Send a channel ID or forward a message from the channel.")

# Handle user input for countdown
async def countdown_input(update: Update, context: CallbackContext):
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)

    if seconds is None or seconds <= 0:
        await update.message.reply_text("Invalid time format! Please enter a valid duration.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{seconds}"),
         InlineKeyboardButton("✏️ Modify", callback_data="set_countdown")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for <b>{format_time(seconds)}</b>?", reply_markup=reply_markup, parse_mode="HTML")

# Confirm and start countdown
async def confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    seconds = int(query.data.split("_")[1])
    message = await query.message.edit_text(f"⏳ Countdown started for <b>{format_time(seconds)}</b>!", parse_mode="HTML")

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
    await message.reply_text("🚨 <b>Time's up!</b> 🚨", parse_mode="HTML")

# Handle channel addition
async def add_channel(update: Update, context: CallbackContext):
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        managed_channels[chat.id] = chat.title
        await update.message.reply_text(f"✅ Added channel: {chat.title}")
    else:
        try:
            chat_id = int(update.message.text)
            managed_channels[chat_id] = f"Channel {chat_id}"
            await update.message.reply_text(f"✅ Added channel: {chat_id}")
        except ValueError:
            await update.message.reply_text("❌ Invalid input. Forward a message from the channel or enter a valid channel ID.")

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

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm, pattern=r"confirm_\d+"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_web).start()
