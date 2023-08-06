from aiogram import Router
from aiogram.filters import Command  
from keyboards import help_msg




router = Router()

router.message.filter(((Command(commands=["help"]))))


@router.message(Command('help'))
async def help(message):
    await message.answer(text='По поводу любых вопросов, пожалуйста, обращайтесь к менеджеру 💞', reply_markup=help_msg())
    
