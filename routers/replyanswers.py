from aiogram import Router, F
import bot_db as db
from redis_storage import redis
from aiogram.methods.send_message import SendMessage
from aiogram.methods.delete_message import DeleteMessage
from bot_db import get_user, get_class_meetings, get_class
import datetime
import useless
import config
import keyboards


router = Router()

router.message.filter(F.text.in_(['Расписание лекций 🗓', 'Информация о курсе 🗂',
                                  'Персональные данные 👤', 'Помощь по боту 🛠', 'Связь с преподавателем 👩🏻‍🏫']))

@router.message(F.text == 'Расписание лекций 🗓')
async def checkMeetingsText(message):
    data = await redis.get(name=message.chat.id)
    if data:
        user_data = await get_user(message.chat.id)
        class_id = user_data[6]
        if class_id and class_id != 0 and user_data[7] == 1:
            text = "Расписание лекций:\n"
            meetings_data = list(await get_class_meetings(class_id))
            if not meetings_data:
                text += "<b>Лекций не найдено.</b>"
            else:
                meetings_data = sorted(meetings_data, key=lambda data: datetime.datetime.fromisoformat(data[2]))
                i = 0
                for meeting_data in meetings_data:
                    i += 1
                    text += f"{i}. {useless.dateToStr(datetime.datetime.fromisoformat(meeting_data[2]))}\n"
            await message.answer(text)
                
        else:
            await message.answer("У Вас нет доступа к курсу.")
    else:
        await message.answer("Вы ещё не зарегестрированы.")
    
@router.message(F.text == 'Информация о курсе 🗂')
async def checkPaymentText(message):
    data = await redis.get(name=message.chat.id)
    if data:
        user_data = await get_user(message.chat.id)
        class_id = user_data[6]
        if class_id and class_id != 0 and user_data[7] == 1:
            class_data = await get_class(class_id)
            start_date = datetime.datetime.fromisoformat(class_data[2])
            if not user_data[8] == 'using':
                months = user_data[5]
                date1 = ' '.join(useless.dateToStr(start_date).split()[1:])
                tarif = useless.tarifName(user_data[4])
                if not months == config.maximum_months:
                    exp_date = start_date + datetime.timedelta(days=30*months)
                    date2 = ' '.join(useless.dateToStr(exp_date).split()[1:])
                    text = (f"Тариф: «{tarif}»\n"
                            f"Дата начала обучения: {date1}.\n"
                            f"Количество оплаченных дней: {months*30}/{config.maximum_months*30}.\n"
                            f"На данный момент доступ к боту закрывается: {date2}.")
                else:
                    exp_date = datetime.datetime.fromisoformat(class_data[3])
                    date2 = ' '.join(useless.dateToStr(exp_date).split()[1:])
                    text = (f"Тариф: «{tarif}»\n"
                            f"Дата начала обучения: {date1}.\n"
                            f"Количество оплаченных дней: {months*30}/{config.maximum_months*30}.\n"
                            f"На данный момент доступ к боту закрывается: {date2} (с окончанием курса).")
            else:
                exp_date = start_date + datetime.timedelta(days=7)
                text = (f"Вы в данный момент пользуетесь бесплатным периодом, действие которого завершится {useless.dateToStr(exp_date)}.")
            await message.answer(text)
        else:
            await message.answer("У Вас нет доступа к курсу.")
    else:
        await message.answer("Вы ещё не зарегестрированы.")

@router.message(F.text == 'Персональные данные 👤')
async def checkInfoText(message, state):
    data = await redis.get(name=message.chat.id)
    if data:
        user_data = await state.get_data()
        if 'name' in user_data and 'changemsg' in user_data:
            await message.answer("Вы ещё не завершили изменение данных, вызванное в прошлый раз.")
        elif 'name' in user_data:
            await message.answer("Вы еще не завершили регистрацию.")
        else:
            if not 'changemsg' in user_data:
                user_data = await get_user(message.chat.id)
                await state.update_data(name=user_data[1], phone=user_data[2], email=user_data[3])
                user_data = dict(zip(['name', 'phone', 'email'], [user_data[1], user_data[2], user_data[3]]))
            else:
                if user_data['changemsg']:
                    await DeleteMessage(chat_id=message.chat.id, message_id=user_data['changemsg'])
            msg = await SendMessage(text=f"Ваши данные:\nФИО: {user_data['name']}.\nНомер телефона: {user_data['phone']}.\n"
                                        f"E-mail: {user_data['email']}.", chat_id=message.chat.id,
                                        reply_markup=keyboards.change_info())
            await state.update_data(changemsg=msg.message_id)
    else:
        await message.answer('Вы ещё не зарегестрированы.')

@router.message(F.text == 'Помощь по боту 🛠')
async def helpText(message):
    await message.answer(text='По поводу любых вопросов, пожалуйста, обращайтесь к менеджеру 💞', reply_markup=keyboards.help_msg())

@router.message(F.text == 'Связь с преподавателем 👩🏻‍🏫')
async def teacherText(message):
    data = await redis.get(name=message.chat.id)
    if data:
        user_data = await db.get_user(message.chat.id)
        access = user_data[7]
        tarif = user_data[4]
        if access == 1:
            if tarif == '2':
                await message.answer(text='Для перехода в диалог нажмите ⬇️', reply_markup=keyboards.teacher())
            else:
                await message.answer(text='Данная функция доступна только в тарифе «Хочу большего».\n'
                                     'Если хотите перейти на тариф «Хочу большего», свяжитесь с нашим менеджером ⬇️',
                                     reply_markup=keyboards.help_msg())
        else:
            await message.answer("У Вас нет доступа к курсу.")
    else:
        await message.answer('Вы ещё не зарегестрированы.')
