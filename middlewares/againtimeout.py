from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from typing import Dict, Any, Callable, Awaitable
import datetime
from config import tryAgainTimeout
from aiogram.methods.answer_callback_query import AnswerCallbackQuery
import useless


class TryAgainMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.user_data = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if 'confirm_data' in event.data:
            lasttime = datetime.datetime.timestamp(datetime.datetime.now())
            user_id = event.message.chat.id
            if not user_id in self.user_data:
                self.user_data[user_id]=0
            if event.data == 'confirm_data_again' and lasttime - self.user_data[user_id] < tryAgainTimeout:
                await AnswerCallbackQuery(callback_query_id=event.id, 
                                        text=f'До повторной отправки осталось {useless.secToStr(tryAgainTimeout - (int(lasttime)-int(self.user_data[user_id])))}.',
                                        show_alert=True)
                return
            else:
                if 'confirm_data' in event.data:
                    self.user_data[user_id] = datetime.datetime.timestamp(datetime.datetime.now())
        return await handler(event, data)
        