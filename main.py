import asyncio
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler,
    CommandHandler, ContextTypes
)
from handlers import (
    start, check_joined, quiz_handler,
    answer_handler, report_handler, feedback_handler
)
from keep_alive import keep_alive

BOT_TOKEN = "7219397761:AAGzeEKdvR8tc1DkH0zoYtrdxYH8J5eS3Jw"

async def run():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_joined, pattern="check_joined"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^(easy_quiz|hard_quiz)$"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer\\|"))
    app.add_handler(CallbackQueryHandler(report_handler, pattern="^report$"))
    app.add_handler(CallbackQueryHandler(feedback_handler, pattern="^feedback$"))

    asyncio.create_task(keep_alive())
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run())
