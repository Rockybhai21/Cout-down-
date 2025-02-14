import json
import os

# File to store managed channels
MANAGED_CHANNELS_FILE = "managed_channels.json"

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
