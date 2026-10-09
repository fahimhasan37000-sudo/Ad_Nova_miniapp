import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from .config import settings

async def main():
    if not settings.bot_token:
        raise RuntimeError("Set BOT_TOKEN in .env before starting the bot")
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    @dp.message(CommandStart())
    async def start(message: Message):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Open Earning App", web_app=WebAppInfo(url=settings.webapp_url))]],
            resize_keyboard=True
        )
        await message.answer(
            f"Welcome to {settings.app_name}!\nOpen the Mini App to view tasks and your balance.",
            reply_markup=keyboard
        )
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
