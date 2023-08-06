from aiogram import Router, F
from aiogram.filters import Command  
from aiogram.fsm.state import State, StatesGroup
from aiogram.methods.edit_message_text import EditMessageText
from aiogram.methods import EditMessageReplyMarkup
from aiogram.methods.send_message import SendMessage
from aiogram.methods.delete_message import DeleteMessage
from aiogram.methods.answer_callback_query import AnswerCallbackQuery
import datetime
from asyncio import sleep
from bot_db import create_user, update_user, get_user, admin_menu_user_update, get_class, get_present_classes, get_class_meetings
from redis_storage import redis
import keyboards
import config
import useless


router = Router()

class Registration(StatesGroup):
    choosing_name = State()
    choosing_phone = State()
    choosing_email = State()
    choosing_first_date = State()

class ChangeInfo(StatesGroup):
    new_name = State()
    new_phone = State()
    new_email = State()

tasks = set()



async def editInfo(user_id: int, user_data: dict, mode: str, msgid: int = None, msgtext: str = None):
    text = f"Ваши данные:\nФИО: {user_data['name']}.\nНомер телефона: {user_data['phone']}.\nE-mail: {user_data['email']}.\n\n"
    namechange = "Введите ФИО полностью."
    phonechange = "Введите номер телефона в формате 79xxxxxxxxxx."
    emailchange = "Введите e-mail."
    if mode == 'changing_name':
        text += "<b>" + namechange + "</b>"
        keyboard = keyboards.user_reg_cancel()
    elif mode == 'changing_phone':
        text += "<b>" + phonechange + "</b>"
        keyboard = keyboards.user_reg_cancel()
    elif mode == 'changing_email':
        text += "<b>" + emailchange + "</b>"
        keyboard = keyboards.user_reg_cancel()
    elif mode == 'after_change':
        text += "<b>Данные успешно изменены</b>"
        keyboard = keyboards.user_reg_change()
        await DeleteMessage(chat_id=user_id, message_id=msgid)
    elif mode == 'free_period_confirming':
        text += "<b>Вы действительно хотите начать 7-дневный пробный период?</b>"
        keyboard = keyboards.user_free_period_confirm()
    elif mode == 'after_free_period_confirm':
        text += f"<b>Пробный период начался. Дата окончания - {useless.dateToStr(user_data['free_expir_date'])}.</b>"
        keyboard = None
    elif mode == 'show_info':
        text2 = ("Записавшись на курс, Вы отправляете заявку администратору. Она будет подтверждена в том случае,"
            " если вы оплатили один из тарифов.\nЕсли Вы хотите попробовать один из наших тарифов, предлагаем Вам бесплатный "
            f"{config.free_period_length}-дневный период.")
        text += text2
        keyboard = keyboards.user_reg_change()
    elif mode == 'after_data_confirm':
        text += "<b>Заявка отправлена. Ожидайте подтверждения администратором.</b>"
        keyboard = None
    elif 'after_changing_' in mode:
        changed = mode.split('_')[2]
        text += "<b>"
        if changed == 'email':
            text += "E-mail успешно изменён."
        elif changed == 'phone':
            text += "Номер телефона успешно изменён."
        elif changed == 'name':
            text += "ФИО успешно изменено."
        text += "</b>"
        keyboard = keyboards.user_reg_change()
        await DeleteMessage(chat_id=user_id, message_id=msgid)
    elif 'same_data_' in mode:
        changed = mode.split('_')[2]
        text += f"<b>Вы ввели: {msgtext}\n"
        text += "Введены те же данные.\n"
        if changed == 'name':
            text += namechange
        elif changed == 'phone':
            text += phonechange
        elif changed == 'email':
            text += emailchange
        text += "</b>"
        keyboard = keyboards.user_reg_cancel()
        await DeleteMessage(chat_id=user_id, message_id=msgid)
    elif 'wrong_data_' in mode:
        changed = mode.split('_')[2]
        text += "<b>"
        if changed == 'nameshort':
            text += "ФИО не может быть пустым.\n" + namechange
        elif changed == 'namelong':
            text += "Введено слишком много символов.\n" + namechange
        elif changed == 'phone':
            if msgtext:
                if len(msgtext) < 150:
                    text += f"Вы ввели: {check(msgtext)}\n"
            text += "Неправильно введён номер телефона.\n" + phonechange
        elif changed == 'email':
            if msgtext:
                if len(msgtext) < 150:
                    text += f"Вы ввели: {check(msgtext)}\n"
                else:
                    text += "Введено слишком много символов.\n"
            text += "Неправильно введён e-mail.\n" + emailchange
        text +=  "</b>"
        keyboard = keyboards.user_reg_cancel()
        await DeleteMessage(chat_id=user_id, message_id=msgid)
    elif mode == 'preconfirm':
        text += f"<b>Вы действительно хотите отправить заявку?</b>"
        keyboard = keyboards.user_tarif_confirm()
    try:
        await EditMessageText(text=text, chat_id=user_id, message_id=user_data['regmes'], parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(f'registration failed to edit:\n{type(e)}: {e}')

def check(text):
    if not text:
        return ''
    else:
        return text

async def editChangeInfo(user_id: int, user_data: dict, mode: str, msg_data : list = None):
    text = (f"Ваши данные:\nФИО: {user_data['name']}.\nНомер телефона: {user_data['phone']}.\n"
            f"E-mail: {user_data['email']}.\n\n")

    namechange = "Введите ФИО полностью."
    phonechange = "Введите номер телефона в формате 79xxxxxxxxxx."
    emailchange = "Введите e-mail."

    if mode == 'casual':
        keyboard = keyboards.change_info()
    elif mode == 'new_name':
        text += "<b>" + namechange + "</b>"
        keyboard = keyboards.change_info_cancel()
    elif mode == 'new_phone':
        text += "<b>" + phonechange + "</b>"
        keyboard = keyboards.change_info_cancel()
    elif mode == 'new_email':
        text += "<b>" + emailchange + "</b>"
        keyboard = keyboards.change_info_cancel()
    elif mode == 'after_name_change':
        text += "<b>ФИО успешно изменено.</b>"
        keyboard = keyboards.change_info()
    elif mode == 'after_phone_change':
        text += "<b>Номер телефона успешно изменён.</b>"
        keyboard = keyboards.change_info()
    elif mode == 'after_email_change':
        text += "<b>E-mail успешно изменён.</b>"
        keyboard = keyboards.change_info()
    elif 'same_data' in mode or 'wrong_data' in mode:
        await DeleteMessage(chat_id=user_id, message_id=msg_data[0])
        if msg_data[1]:
            if len(msg_data[1]) < 120:
                text += f"<b>Вы ввели: {msg_data[1]}\n"
            else:
                text += "<b>Введено слишком много символов.\n"
        else:
            text += "<b>В сообщении отсутствует текст.\n"
        if 'same_data' in mode:
            text += "Введены те же данные.\n"
        else:
            text += "Данные введены неправильно.\n"
        if 'name' in mode:
            text += namechange
        elif 'phone' in mode:
            text += phonechange
        elif 'email' in mode:
            text += emailchange
        text += "</b>"
        keyboard = keyboards.change_info_cancel()
    elif mode == 'finish':
        keyboard = None 
    try:
        await EditMessageText(text=text, chat_id=user_id, message_id=user_data['changemsg'], parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(f'failed to edit changeinfo msg:\n{type(e)}: {e}')

    


@router.message(Command(commands='cancel'))
async def cancel(message, state):
    current_state = await state.get_state()
    if current_state == None:
        msg = await message.answer('Отменять нечего.')
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
        return
    user_data = await state.get_data()
    await state.set_state(None)
    if 'name' in user_data and 'phone' in user_data and 'email' in user_data:
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await editInfo(message.chat.id, user_data, 'show_info')
    else:
        text = 'Ввод данных отменён. Для повторной регистрации введите /start.'
        await message.answer(text)


@router.message(Registration.choosing_name, ((F.text.len() > 0) & (F.text.len() < 120)))
async def name(message, state):
    user_data = await state.get_data()
    if 'name' in user_data and user_data['name'] == message.text:
        await editInfo(message.chat.id, user_data, 'same_data_name', message.message_id, check(message.text))
    else:
        await state.update_data(name=message.text)
        if 'phone' in user_data:
            user_data = await state.get_data()
            await editInfo(message.chat.id, user_data, 'after_changing_name', message.message_id)
            await state.set_state(None)

        else:
            await message.answer('Введите номер телефона в формате 79xxxxxxxxx.')
            await state.set_state(Registration.choosing_phone)
@router.message(Registration.choosing_name)
async def wrongName(message, state):
    user_data = await state.get_data()
    if not message.text:
        text = "ФИО не может быть пустым."
        mode = 'nameshort'
    else:
        text = "Введено слишком много символов."
        mode = 'namelong'
    if not 'name' in user_data:
        msg = await message.answer(text)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await sleep(5)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
    else:

        await editInfo(message.chat.id, user_data, f'wrong_data_{mode}', message.message_id, check(message.text))

@router.message(Registration.choosing_phone, ((F.text.startswith('7')) & (F.text.len() == 11) & (F.text.isdigit())))
async def phone(message, state):
    user_data = await state.get_data()
    if 'phone' in user_data and user_data['phone'] == message.text:
        await editInfo(message.chat.id, user_data, 'same_data_phone', message.message_id, check(message.text))
    else:
        await state.update_data(phone=message.text)
        if 'email' in user_data:
            user_data = await state.get_data()
            await editInfo(message.chat.id, user_data, 'after_changing_phone', message.message_id)
            await state.set_state(None)
        else:
            await message.answer('Введите e-mail.')
            await state.set_state(Registration.choosing_email)
@router.message(Registration.choosing_phone)
async def wrongNumber(message, state):
    user_data = await state.get_data()
    if not 'phone' in user_data:
        msg = await message.answer(f"Вы ввели: {check(message.text)}\nНеправильно введён номер телефона.")
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await sleep(5)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
    else:
        await editInfo(message.chat.id, user_data, 'wrong_data_phone', message.message_id, check(message.text))

@router.message(Registration.choosing_email, ((F.text.regexp(r'[^@]+@[^@]+\.[^@]+')) & (F.text.len() < 50)))
async def email(message, state):
    user_data = await state.get_data()
    if 'email' in user_data and user_data['email'] == message.text:
        await editInfo(message.chat.id, user_data, 'same_data_email', message.message_id, check(message.text))
    else:
        if 'email' in user_data:
            await state.update_data(email=message.text)
            user_data = await state.get_data()
            await editInfo(message.chat.id, user_data, 'after_changing_email', message.message_id)
            await state.set_state(None)
        else:
            await state.update_data(email=message.text)
            user_data = await state.get_data()
            await redis.set(name=message.chat.id, value=1)
            regmes = await message.answer(f"Ваши данные:\nФИО: {user_data['name']}.\nНомер телефона: {user_data['phone']}.\n"
                                        f"E-mail: {user_data['email']}.", reply_markup=keyboards.user_reg_change())
            await state.update_data(regmes=regmes.message_id)
            user_data = await state.get_data()
            await editInfo(message.chat.id, user_data, 'show_info')
            await state.set_state(None)
@router.message(Registration.choosing_email)
async def wrongEmail(message, state):
    user_data = await state.get_data()
    if not 'email' in user_data:
        if len(message.text) < 50:
            msg = await message.answer(f"Вы ввели: {check(message.text)}\nНеправильно введён e-mail.")
        else:
            msg = await message.answer("Неправильно введён e-mail.")
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await sleep(5)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
    else:
        await editInfo(message.chat.id, user_data, 'wrong_data_email', message.message_id, check(message.text))


@router.message(ChangeInfo.new_name, ((F.text.len() > 0) & (F.text.len() < 120)))
async def newName(message, state):
    user_data = await state.get_data()
    if user_data['name'] == message.text:
        await editChangeInfo(message.chat.id, user_data, 'same_data_name', [message.message_id, check(message.text)])
    else:
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.update_data(name=message.text)
        user_data = await state.get_data()
        await editChangeInfo(message.chat.id, user_data, 'after_name_change')
        await state.set_state(None)
@router.message(ChangeInfo.new_name)
async def wrongNewName(message, state):
    user_data = await state.get_data()
    await editChangeInfo(message.chat.id, user_data, 'wrong_data_name', [message.message_id, check(message.text)])


@router.message(ChangeInfo.new_phone, ((F.text.startswith('7')) & (F.text.len() == 11) & (F.text.isdigit())))
async def newPhone(message, state):
    user_data = await state.get_data()
    if user_data['phone'] == message.text:
        await editChangeInfo(message.chat.id, user_data, 'same_data_phone', [message.message_id, check(message.text)])
    else:
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.update_data(phone=message.text)
        user_data = await state.get_data()
        await editChangeInfo(message.chat.id, user_data, 'after_phone_change')
        await state.set_state(None)
@router.message(ChangeInfo.new_phone)
async def wrongNewPhone(message, state):
    user_data = await state.get_data()
    await editChangeInfo(message.chat.id, user_data, 'wrong_data_phone', [message.message_id, check(message.text)])


@router.message(ChangeInfo.new_email, ((F.text.regexp(r'[^@]+@[^@]+\.[^@]+')) & (F.text.len() < 50)))
async def newEmail(message, state):
    user_data = await state.get_data()
    if user_data['email'] == message.text:
        await editChangeInfo(message.chat.id, user_data, 'same_data_email', [message.message_id, check(message.text)])
    else:
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.update_data(email=message.text)
        user_data = await state.get_data()
        await editChangeInfo(message.chat.id, user_data, 'after_email_change')
        await state.set_state(None)
@router.message(ChangeInfo.new_email)
async def wrongNewEmail(message, state):
    user_data = await state.get_data()
    await editChangeInfo(message.chat.id, user_data, 'wrong_data_email', [message.message_id, check(message.text)])


@router.message(Command(commands=['start']))
async def start(message):
    user_status = await redis.get(name=message.chat.id)
    if not user_status:
        await create_user(message.from_user.id)
        keyboard = keyboards.register_start()
    else:
        keyboard = None
    await message.answer("Hello there!\nМеня зовут Wiserbot, я бот, который помогает "
    "автоматизировать процесс обучения. Буду сопровождать Вас в течение всего курса🤗", reply_markup=keyboard)



@router.message(Command('changepersonaldata'))
async def checkInfo(message, state):
    data = await redis.get(name=message.chat.id)
    if data:
        user_data = await state.get_data()
        if not 'name' in user_data:
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
            await message.answer("Вы еще не завершили регистрацию.")
    else:
        await message.answer('Вы еще не зарегестрированы.')

@router.message(Command('checklectures'))
async def checkMeetings(message):
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
            await message.answer("У вас нет доступа к курсу.")
    else:
        await message.answer("Вы еще не зарегестрированы.")

@router.message(Command('checkinfo'))
async def checkPayment(message):
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
            await message.answer("У вас нет доступа к курсу.")
    else:
        await message.answer("Вы еще не зарегестрированы.")


@router.callback_query()
async def call(call, state):
    try:
        if 'change' in call.data:
            user_data = await state.get_data()
            if 'fio' in call.data:
                await editInfo(call.message.chat.id, user_data, 'changing_name')
                await state.set_state(Registration.choosing_name)
            elif 'phone' in call.data:
                await editInfo(call.message.chat.id, user_data, 'changing_phone')
                await state.set_state(Registration.choosing_phone)
            elif 'email' in call.data:
                await editInfo(call.message.chat.id, user_data, 'changing_email')
                await state.set_state(Registration.choosing_email)
            elif call.data == 'cancel_user_change':
                await editInfo(call.message.chat.id, user_data, 'show_info')
                await state.set_state(None)

        elif call.data == 'register':
            await state.set_state(Registration.choosing_name)
            await EditMessageText(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                text="Hello there!\nМеня зовут Wiserbot, я бот, который помогает "
                                "автоматизировать процесс обучения. Буду сопровождать вас в течение всего курса🤗\n\n"
                                "Для отмены регистрации введите /cancel.", reply_markup=None)
            await call.message.answer("Введите Ваше ФИО полностью.")
        
        elif call.data == 'confirm_data' or call.data == 'confirm_data_again':
            user_data = await get_user(call.message.chat.id)
            access = user_data[7]
            free_status = user_data[8]
            match free_status:
                case '0':
                    free_status = 'Не пользовался'
                case 'expired':
                    free_status = 'Истёк'
                case 'using':
                    free_status = 'Пользуется сейчас'
            if access == 0:
                if call.data == 'confirm_data':
                    
                    chat_id = call.message.chat.id
                    await state.update_data(tarif='Не выбран', paid_months=0, access=0, class_id=0)
                    user_data = await state.get_data()
                    await update_user(data=user_data, user_id=call.message.chat.id, mode='registration_complete')
                    class_info = 'Не выбран'
                    for admin_id in config.admins:
                        await SendMessage(chat_id=admin_id, text=f"Поступил запрос от пользователя с ID: {chat_id}.\nФИО: {user_data['name']}.\n"
                                        f"Номер телефона: {user_data['phone']}.\nЭлектронная почта: {user_data['email']}.\n"
                                        f"Тариф: {useless.tarifName(user_data['tarif'])}.\nКоличество оплаченных месяцев: {user_data['paid_months']}.\n"
                                        f"Поток: {class_info}.\nСтатус пробного периода: {free_status}.\n", 
                                        parse_mode='HTML', reply_markup=keyboards.KBBuilder(chat_id))
                    await editInfo(call.message.chat.id, user_data, 'after_data_confirm')
                    await state.clear()

                elif call.data == 'confirm_data_again':

                    await EditMessageText(text='Повторный запрос успешно отправлен. Ожидайте подтверждения администратором.', 
                                        chat_id=call.message.chat.id, message_id=call.message.message_id)
                    if user_data[6] == 0:
                        class_info = 'Не выбран'
                    else:
                        class_data = await get_class(user_data[6])
                        class_info = f"{class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})"
                    for admin_id in config.admins:
                        await SendMessage(chat_id=admin_id, text=f"Поступил запрос от пользователя с ID: {call.message.chat.id}.\nФИО: {user_data[1]}.\n"
                                        f"Номер телефона: {user_data[2]}.\nЭлектронная почта: {user_data[3]}.\n"
                                        f"Тариф: {useless.tarifName(user_data[4])}.\nКоличество оплаченных месяцев: {user_data[5]}.\n"
                                        f"Поток: {class_info}.\nСтатус пробного периода: {free_status}.\n", 
                                        parse_mode='HTML', reply_markup=keyboards.KBBuilder(call.message.chat.id))
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Вам уже открыт доступ к одному из тарифов или бесплатному периоду.", 
                                        show_alert=True)
                await state.clear()
                await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
            
        
        elif call.data == 'preconfirm':
            start_date = await redis.get(name='startdate')
            if start_date:
                start_date = datetime.datetime.fromisoformat(str(start_date.decode()))
                if datetime.datetime.now() < start_date + datetime.timedelta(days=14):
                    user_data = await state.get_data()
                    await editInfo(call.message.chat.id, user_data, 'preconfirm')
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text='С момента старта курса прошло более двух недель. Ожидайте начала нового набора на курс.',
                                            show_alert=True)
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Подождите, администрация еще не настроила бота.", show_alert=True)
        
        
        elif call.data == 'try_free':
            start_date = await redis.get(name='startdate')
            if start_date:
                start_date = datetime.datetime.fromisoformat(str(start_date.decode()))
                if datetime.datetime.now() < start_date + datetime.timedelta(days=7):
                    user_data = await state.get_data()
                    await editInfo(call.message.chat.id, user_data, 'free_period_confirming')
                else:
                    text = "С момента начала курса прошло более недели. "
                    if datetime.datetime.now() < start_date + datetime.timedelta(days=14):
                        text += "Вы всё ещё можете получить платный доступ к курсу."
                    else:
                        text += "Ожидайте начала нового набора на курс."
                    await AnswerCallbackQuery(callback_query_id=call.id, text=text, show_alert=True)
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Подождите, администрация еще не настроила бота.", show_alert=True)

            
        elif call.data == 'confirm_free_period' or call.data == 'confirm_free_from_again':
            user_data = await get_user(call.message.chat.id)
            access = user_data[7]
            if access == 0 and user_data[8] != 'expired':
                classes_data = await get_present_classes()
                min_date = datetime.datetime.fromisoformat('2099-12-31')
                class_id = None
                for class_data in classes_data:
                    if datetime.datetime.fromisoformat(class_data[2]) < min_date:
                        min_date = datetime.datetime.fromisoformat(class_data[2])
                        class_id = class_data[0]
                exp_date = min_date + datetime.timedelta(days=7)
                if call.data == 'confirm_free_period':
                    user_data = await state.get_data()
                    user_data = dict(zip(['name', 'phone', 'email', 'free_expir_date', 'regmes'], 
                                        [user_data['name'], user_data['phone'], user_data['email'], exp_date, user_data['regmes']]))
                    
                    await admin_menu_user_update(call.message.chat.id, {'name': user_data['name'], 'phone': user_data['phone'],
                                                'email': user_data['email'], 'tarif': 0, 'paid_months': 0, 
                                                'class_id': class_id, 'access': 1, 'free_period_status': 'using'})
                    
                    await editInfo(call.message.chat.id, user_data, 'after_free_period_confirm')
                    await SendMessage(chat_id=call.message.chat.id, text="Доступ к боту открыт.", reply_markup=keyboards.reply(False))
                    await state.clear()
                else:
                    await admin_menu_user_update(call.message.chat.id, {'tarif': 0, 'paid_months': 0, 
                                                'class_id': 0, 'access': 1, 'free_period_status': 'using'})
                    await EditMessageText(text="<b>Пробный период успешно активирован.\n"
                                            f"Дата окончания: {useless.dateToStr(exp_date)}.</b>", 
                                            chat_id=call.message.chat.id,
                                            message_id=call.message.message_id, parse_mode='HTML', reply_markup=keyboards.reply(False))  
                user_data = await get_user(call.message.chat.id)
                class_data = await get_class(class_id)
                for admin_id in config.admins:
                    await SendMessage(chat_id=admin_id, text=(f"Пользователь {call.message.chat.id} <b>начал пробный период</b>. Информация о пользователе:\n"
                                    f"ФИО: {user_data[1]}.\nНомер телефона: {user_data[2]}.\n"
                                    f"E-mail: {user_data[3]}.\n"
                                    f"Поток: {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n"
                                    f"Дата окончания пробного периода: {useless.dateToStr(exp_date)}."),
                                    parse_mode='HTML')
                
            else:
                if access == 1:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Вам уже открыт доступ к одному из тарифов или бесплатному периоду.", 
                                            show_alert=True)
                elif user_data[8] == 'expired':
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Вы уже пользовались пробным периодом.", 
                                            show_alert=True)
                await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
                await state.clear()
            
                
        elif call.data == 'try_free_from_again':
            start_date = await redis.get(name='startdate')
            if start_date:
                start_date = datetime.datetime.fromisoformat(str(start_date.decode()))
                if start_date + datetime.timedelta(days=7) > datetime.datetime.now():
                    await EditMessageText(text=f"Вы действительно хотите начать {config.free_period_length}-дневный период?",
                                        chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                        reply_markup=keyboards.cancel_free_from_again())       
                else:
                    text = "С момента начала курса прошло более недели. "
                    if datetime.datetime.now() < start_date + datetime.timedelta(days=14):
                        text += "Вы всё ещё можете получить платный доступ к курсу."
                    else:
                        text += "Ожидайте начала нового набора на курс."
                    await AnswerCallbackQuery(callback_query_id=call.id, text=text, show_alert=True)
        
        elif call.data == 'reject_free_from_again':
            await EditMessageText(text=f"Ваш запрос отклонен. Повторный запос можно будет отправить через "
                            f"{config.tryAgainTimeout//60} минут.", chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=keyboards.reject_access_adm('0'))
            
        elif 'new_' in call.data:
            user_data = await state.get_data()
            user_id = call.message.chat.id
            if call.data == 'new_name':
                await editChangeInfo(user_id, user_data, 'new_name')
                await state.set_state(ChangeInfo.new_name)
            elif call.data == 'new_phone':
                await editChangeInfo(user_id, user_data, 'new_phone')
                await state.set_state(ChangeInfo.new_phone)
            elif call.data == 'new_email':
                await editChangeInfo(user_id, user_data, 'new_email')
                await state.set_state(ChangeInfo.new_email)
            elif call.data == 'new_cancel':
                await editChangeInfo(user_id, user_data, 'casual')
                await state.set_state(None)
            elif call.data == 'new_finish':
                await editChangeInfo(user_id, user_data, 'finish')
                await admin_menu_user_update(user_id=user_id, data={'name': user_data['name'], 'phone': user_data['phone'], 'email': user_data['email']})
                await state.clear()
            elif call.data == 'new_cancel_all':
                await editChangeInfo(user_id, user_data, 'finish')
                await state.clear()

        elif call.data == 'confirm_data_after_free':
            await call.message.answer('Запрос успешно отправлен. Ожидайте подтверждения администратором.')
            user_data = await get_user(call.message.chat.id)
            free_status = user_data[8]
            match free_status:
                case '0':
                    free_status = 'Не пользовался'
                case 'expired':
                    free_status = 'Истёк'
                case _:
                    free_status = 'Пользуется сейчас'
            if user_data[6] == 0:
                        class_info = 'Не выбран'
            else:
                class_data = await get_class(user_data[6])
                class_info = f"{class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})"
            for admin_id in config.admins:
                await SendMessage(chat_id=admin_id, text=f"Поступил запрос после пользования бесплатным периодом "
                                f"от пользователя с ID: {call.message.chat.id}.\nФИО: {user_data[1]}.\n"
                                f"Номер телефона: {user_data[2]}.\nЭлектронная почта: {user_data[3]}.\n"
                                f"Тариф: {useless.tarifName(user_data[4])}.\nКоличество оплаченных месяцев: {user_data[5]}.\n"
                                f"Поток: {class_info}.\nСтатус пробного периода: {free_status}.\n", 
                                parse_mode='HTML', reply_markup=keyboards.KBBuilder(call.message.chat.id))
        elif call.data == 'i_paid':
            await EditMessageReplyMarkup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            user_data = await get_user(call.message.chat.id)
            for admin_id in config.admins:
                await SendMessage(chat_id=admin_id, text=f"Пользователь {user_data[1]} с ID {user_data[0]} возможно оплатил "  
                                    "следующий месяц, проверьте и воспользуйтесь кнопками ниже. Вы можете сделать то же самое с помощью" 
                                    " /user_menu.", reply_markup=keyboards.i_paid_admin(call.message.chat.id))
        elif call.data == 'i_will_pay':
            await EditMessageReplyMarkup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id,
                                  text="Что-то пошло не так. Попробуйте заново вызвать сообщение, кнопку на котором вы нажали.",
                                  show_alert=True)
