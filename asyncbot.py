import dispatcher
import asyncio
from bot_db import db_start
from notifications import botStartNotifTasks, botRestart
from datetime import datetime
from config import admins
import logging

tasks = set()
#import tracemalloc

#tracemalloc.start()

async def main():
    global tasks
    logging.basicConfig(
        level=logging.INFO,
        filename = "logs.log",
        format = "%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
        datefmt='%H:%M:%S',
    )
    logging.info('Hello')
    print("starting...")
    now = datetime.timestamp(datetime.now())
    dp = dispatcher.dp
    bot = dispatcher.bot
    await db_start()
    tasks.update(await botStartNotifTasks())
    #tasks.add(asyncio.create_task(coro=botRestart(), name="restart"))
    await bot.delete_webhook(drop_pending_updates=True)
    print(f"successfully started in {datetime.timestamp(datetime.now()) - now} sec")
    await bot.send_message(chat_id=1216178672, text="Бот запущен.", disable_notification=True)
    await dp.start_polling(bot, polling_timeout=10)
    

if __name__ == '__main__':
    asyncio.run(main())