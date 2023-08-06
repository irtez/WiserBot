from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Dict, Any, Callable, Awaitable
import datetime
from aiogram.methods.delete_message import DeleteMessage
from config import bot_id
from redis_storage import redis


class SpamMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.user_data = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        lasttime = datetime.datetime.timestamp(datetime.datetime.now())
        user_id = event.chat.id
        if not user_id in self.user_data:
            self.user_data[user_id]=0
        if lasttime - self.user_data[user_id] < 1 and event.from_user.id != bot_id:
            self.user_data[user_id] = lasttime
            await DeleteMessage(message_id=event.message_id, chat_id=user_id)
        else:
            self.user_data[user_id] = lasttime
            return await handler(event, data)