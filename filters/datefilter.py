from aiogram.filters import Filter
from aiogram.types import Message
from datetime import datetime
from re import match
import useless

class DateFilter(Filter):
    def __init__(self, regexp) -> None:
        self.regexp = regexp


    async def __call__(self, message: Message) -> bool:
        if not match(self.regexp, message.text):
            return False
        newdate = useless.textToDatetime(message.text)
        now = datetime.now()  
        return newdate > now
