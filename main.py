def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link_channel", link_channel))  # Link a channel
    app.add_handler(CommandHandler("linked_channels", show_linked_channels))  # Show linked channels
    app.add_handler(CommandHandler("start_channel_countdown", start_channel_countdown))  # Start countdown for a channel
    app.add_handler(CallbackQueryHandler(confirm_channel_countdown, pattern=r"start_countdown_\d+"))  # Handle channel selection
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, channel_countdown_input))  # Handle countdown input for channels
    app.add_handler(CallbackQueryHandler(confirm_channel_countdown, pattern=r"confirm_channel_countdown_\d+_\d+"))  # Confirm channel countdown
    app.add_handler(CommandHandler("cancel", cancel_countdown))
    app.add_handler(CommandHandler("set_sticker", set_sticker))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm, pattern=r"confirm_\d+"))
    
    print("Bot is running...")
    app.run_polling()
