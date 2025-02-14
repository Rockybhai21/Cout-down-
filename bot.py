import asyncio
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
STICKER_ID = "CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ"
MANAGED_CHATS_FILE = "managed_chats.json"

# Load managed chats (groups/channels)
def load_managed_chats():
    if os.path.exists(MANAGED_CHATS_FILE):
        with open(MANAGED_CHATS_FILE, "r") as file:
            return json.load(file)
    return {}

# Save managed chats
def save_managed_chats(chats):
    with open(MANAGED_CHATS_FILE, "w") as file:
        json.dump(chats, file)

# Format time function
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

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

# Start command
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏳ Set Countdown", callback_data="set_countdown")],
        [InlineKeyboardButton("📢 Manage Chats", callback_data="manage_chats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

# Handle button presses
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "set_countdown":
        await query.message.edit_text("Enter the countdown duration (e.g., '2 hours 30 minutes'):")
    elif query.data == "manage_chats":
        await query.message.edit_text("Send the chat ID to link it.")

# Link a chat by ID
async def link_chat_by_id(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        chat_id = int(update.message.text)
        managed_chats = load_managed_chats()
        if str(user_id) not in managed_chats:
            managed_chats[str(user_id)] = []
        managed_chats[str(user_id)].append({"chat_id": chat_id, "title": f"Chat {chat_id}"})
        save_managed_chats(managed_chats)
        await update.message.reply_text(f"✅ Linked chat: {chat_id}")
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please enter a valid chat ID.")

# Show linked chats
async def show_linked_chats(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    managed_chats = load_managed_chats()
    if str(user_id) in managed_chats and managed_chats[str(user_id)]:
        chats_list = "\n".join([f"{chat['title']} (ID: {chat['chat_id']})" for chat in managed_chats[str(user_id)]])
        await update.message.reply_text(f"📢 Your linked chats:\n{chats_list}")
    else:
        await update.message.reply_text("❌ You have no linked chats.")

# Start a countdown for a linked chat
async def start_chat_countdown(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    managed_chats = load_managed_chats()
    if str(user_id) not in managed_chats or not managed_chats[str(user_id)]:
        await update.message.reply_text("❌ You have no linked chats.")
        return

    # Ask the user to select a chat
    keyboard = [[InlineKeyboardButton(chat["title"], callback_data=f"start_countdown_{chat['chat_id']}")]
                for chat in managed_chats[str(user_id)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📢 Select a chat to start the countdown:", reply_markup=reply_markup)

# Handle countdown input for a chat
async def chat_countdown_input(update: Update, context: CallbackContext):
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)

    if seconds is None or seconds <= 0:
        await update.message.reply_text("Invalid time format! Please enter a valid duration.")
        return

    chat_id = context.user_data.get("selected_chat_id")
    if not chat_id:
        await update.message.reply_text("❌ No chat selected.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_chat_countdown_{chat_id}_{seconds}"),
         InlineKeyboardButton("✏️ Modify", callback_data=f"start_countdown_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for <b>{format_time(seconds)}</b> in chat?", reply_markup=reply_markup, parse_mode="HTML")

# Confirm and start countdown for a chat
async def confirm_chat_countdown(update: Update, context: CallbackContext):
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

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link_chat", link_chat_by_id))
    app.add_handler(CommandHandler("linked_chats", show_linked_chats))
    app.add_handler(CommandHandler("start_chat_countdown", start_chat_countdown))
    app.add_handler(CallbackQueryHandler(confirm_chat_countdown, pattern=r"start_countdown_\d+"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_chat_countdown, pattern=r"confirm_chat_countdown_\d+_\d+"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
