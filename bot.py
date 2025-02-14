import json
import os
import asyncio
import logging
import re
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from flask import Flask
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv("TOKEN")
STICKER_ID = "CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ"
COUNTDOWN_FILE = "countdowns.json"
HISTORY_FILE = "history.json"
ADMIN_IDS = [123456789]  # Replace with actual admin user IDs
MANAGED_CHANNELS_FILE = "managed_channels.json"
# Store countdowns and channels
user_time = {}
active_countdowns = {}
managed_channels = {}

# Load and save functions for countdowns and history
def load_countdowns():
    if os.path.exists(COUNTDOWN_FILE):
        with open(COUNTDOWN_FILE, "r") as file:
            return json.load(file)
    return {}

def save_countdowns(countdowns):
    with open(COUNTDOWN_FILE, "w") as file:
        json.dump(countdowns, file)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file)

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
    user_id = update.effective_user.id
    countdowns = load_countdowns()
    if user_id not in countdowns:
        countdowns[user_id] = []
    countdowns[user_id].append(seconds)
    save_countdowns(countdowns)

    history = load_history()
    history.append({"user_id": user_id, "duration": seconds, "timestamp": datetime.now().isoformat()})
    save_history(history)

    message = await query.message.edit_text(f"⏳ Countdown started for <b>{format_time(seconds)}</b>!", parse_mode="HTML")

    # Post to managed channels
    for chat_id in managed_channels:
        await context.bot.send_message(chat_id, f"⏳ Countdown started for <b>{format_time(seconds)}</b>!", parse_mode="HTML")

    # Start countdown
    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"⏳ Countdown: <b>{format_time(i)}</b> remaining...", parse_mode="HTML")

            # Send notification at specific intervals
            if i % 300 == 0:  # Every 5 minutes
                await message.reply_text(f"⏳ <b>{format_time(i)}</b> remaining...", parse_mode="HTML")

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
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to add channels.")
        return

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

# Cancel an ongoing countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    countdowns = load_countdowns()
    if user_id in countdowns:
        del countdowns[user_id]
        save_countdowns(countdowns)
        await update.message.reply_text("Countdown cancelled.")
    else:
        await update.message.reply_text("No active countdown to cancel.")

# Set custom sticker for countdown alerts
async def set_sticker(update: Update, context: CallbackContext):
    if update.message.sticker:
        global STICKER_ID
        STICKER_ID = update.message.sticker.file_id
        await update.message.reply_text("✅ Sticker set for countdown alerts.")
    else:
        await update.message.reply_text("❌ Please send a sticker to set it for countdown alerts.")

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

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_web).start()

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CommandHandler("cancel", cancel_countdown))
    app.add_handler(CommandHandler("set_sticker", set_sticker))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm, pattern=r"confirm_\d+"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
# Load managed channels
def load_managed_channels():
    if os.path.exists(MANAGED_CHANNELS_FILE):
        with open(MANAGED_CHANNELS_FILE, "r") as file:
            return json.load(file)
    return {}

# Save managed channels
def save_managed_channels(channels):
    with open(MANAGED_CHANNELS_FILE, "w") as file:
        json.dump(channels, file)

# Link a channel to a user
async def link_channel(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        managed_channels = load_managed_channels()
        if str(user_id) not in managed_channels:
            managed_channels[str(user_id)] = []
        managed_channels[str(user_id)].append({"chat_id": chat.id, "title": chat.title})
        save_managed_channels(managed_channels)
        await update.message.reply_text(f"✅ Linked channel: {chat.title}")
    else:
        try:
            chat_id = int(update.message.text)
            managed_channels = load_managed_channels()
            if str(user_id) not in managed_channels:
                managed_channels[str(user_id)] = []
            managed_channels[str(user_id)].append({"chat_id": chat_id, "title": f"Channel {chat_id}"})
            save_managed_channels(managed_channels)
            await update.message.reply_text(f"✅ Linked channel: {chat_id}")
        except ValueError:
            await update.message.reply_text("❌ Invalid input. Forward a message from the channel or enter a valid channel ID.")

# Show linked channels
async def show_linked_channels(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    managed_channels = load_managed_channels()
    if str(user_id) in managed_channels and managed_channels[str(user_id)]:
        channels_list = "\n".join([f"{channel['title']} (ID: {channel['chat_id']})" for channel in managed_channels[str(user_id)]])
        await update.message.reply_text(f"📢 Your linked channels:\n{channels_list}")
    else:
        await update.message.reply_text("❌ You have no linked channels.")

# Start a countdown for a linked channel
async def start_channel_countdown(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    managed_channels = load_managed_channels()
    if str(user_id) not in managed_channels or not managed_channels[str(user_id)]:
        await update.message.reply_text("❌ You have no linked channels.")
        return

    # Ask the user to select a channel
    keyboard = [[InlineKeyboardButton(channel["title"], callback_data=f"start_countdown_{channel['chat_id']}")]
                for channel in managed_channels[str(user_id)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📢 Select a channel to start the countdown:", reply_markup=reply_markup)

# Handle countdown confirmation for a channel
async def confirm_channel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.split("_")[2])
    await query.message.edit_text(f"Enter the countdown duration for channel (e.g., '2 hours 30 minutes'):")

    # Store the selected channel ID in context
    context.user_data["selected_channel_id"] = chat_id

# Handle countdown input for a channel
async def channel_countdown_input(update: Update, context: CallbackContext):
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)

    if seconds is None or seconds <= 0:
        await update.message.reply_text("Invalid time format! Please enter a valid duration.")
        return

    chat_id = context.user_data.get("selected_channel_id")
    if not chat_id:
        await update.message.reply_text("❌ No channel selected.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_channel_countdown_{chat_id}_{seconds}"),
         InlineKeyboardButton("✏️ Modify", callback_data=f"start_countdown_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for <b>{format_time(seconds)}</b> in channel?", reply_markup=reply_markup, parse_mode="HTML")

# Confirm and start countdown for a channel
async def confirm_channel_countdown(update: Update, context: CallbackContext):
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
