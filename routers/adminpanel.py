from aiogram import Router, F
from aiogram.filters import Command  
from aiogram.fsm.state import State, StatesGroup
from aiogram.methods.send_audio import SendAudio
from aiogram.methods.send_video import SendVideo
from aiogram.methods.send_voice import SendVoice
from aiogram.methods.send_video_note import SendVideoNote
from aiogram.methods.edit_message_text import EditMessageText
from aiogram.methods import EditMessageReplyMarkup
from aiogram.methods.send_message import SendMessage
from aiogram.methods.delete_message import DeleteMessage
from aiogram.methods.answer_callback_query import AnswerCallbackQuery
from aiogram.methods.send_document import SendDocument
from aiogram.methods.send_chat_action import SendChatAction
from aiogram.methods.send_photo import SendPhoto
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
import config
from redis_storage import redis
import bot_db as db
from routers.registration import Registration
from asyncio import sleep
import keyboards
from filters.datefilter import DateFilter
from datetime import datetime, timedelta
import useless
import notifications
import asyncio
import csv
from pyexcel.cookbook import merge_all_to_a_book
import glob
import os

router = Router()


router.message.filter(F.from_user.id.in_(config.admins))
router.callback_query.filter(F.from_user.id.in_(config.admins))

class AdminPanel(StatesGroup):
    choosing_first_payment_date = State()
    choose_next_meeting_date = State()
    choose_next_meeting_link = State()
    choosing_name = State()

class ClassPanel(StatesGroup):
    edit_current_class_name = State()
    edit_current_class_startdate = State()
    edit_current_class_finishdate = State()
    edit_new_class_name = State()
    edit_new_class_startdate = State()
    edit_new_class_finishdate = State()

class FilePanel(StatesGroup):
    file_input = State()

class MailPanel(StatesGroup):
    message_input = State()

notif_tasks = set()



@router.message(Command(commands='cancel'))
async def cancel(message, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state == None:
        msg = await message.answer('Отменять нечего.')
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
        return
    elif cur_state == Registration.choosing_first_date:
        await message.answer('Операция отменена.')
        await state.set_state(None)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif cur_state == AdminPanel.choosing_first_payment_date:
        admin_data = await state.get_data()
        user_id = admin_data['current_id']
        user_data = await db.get_user(user_id)
        await showAdminInfo(user_data, message.chat.id, user_id, admin_data['user_menu_msg'], 'show_info')
        msg = await message.answer('Операция отменена.')
        await state.set_state(None)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
    elif cur_state == AdminPanel.choosing_id:
        admin_data = await state.get_data()
        await EditMessageText(text='Меню управления пользователями.', chat_id=message.chat.id, 
                        message_id=admin_data['user_menu_msg'], reply_markup=keyboards.admin_user_menu_begin())
        msg = await message.answer('Операция отменена.')
        await state.set_state(None)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)
    else:
        msg = await message.answer('Операция отменена.')
        await state.set_state(None)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await DeleteMessage(chat_id=message.chat.id, message_id=msg.message_id)

@router.message(AdminPanel.choosing_name)
async def choose_name(message, state):
    data = await db.search_user(message.text)
    user_data = await state.get_data()
    if len(data) > 0 and len(data) <= 10:
        await showAdminInfo(data, message.chat.id, message.text, user_data['user_menu_msg'], 'choose_name_2')
        await state.set_state(None)
    elif len(data) > 10:
        await showAdminInfo(data, message.chat.id, message.text, user_data['user_menu_msg'], 'choose_name_too_many')
    elif len(data) == 0:
        await showAdminInfo(data, message.chat.id, message.text, user_data['user_menu_msg'], 'choose_name_nothing')
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    
@router.message(AdminPanel.choose_next_meeting_date, DateFilter(config.datetime_regexp))
async def meeting_date_change(message, state):
    #meetings_menu_msg=msg.message_id, new_meeting_date=None, new_meeting_link=None, current_meeting_class=None, current_meeting_id=None
    await state.set_state(None)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    msg_id = admin_data['meetings_menu_msg']
    meeting_id = admin_data['current_meeting_id']
    new_date = useless.datetoYYYYMMDD(message.text)
    if meeting_id == 'new':
        await state.update_data(new_meeting_date=new_date)
        admin_data = await state.get_data()
        data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                    admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
        await showMeetingInfo(data, message.chat.id, msg_id, 'create_new')
    else:
        meeting_data = await db.get_meeting(meeting_id)
        class_id = meeting_data[1]
        class_data = await db.get_class(class_id)
        startdate = datetime.fromisoformat(class_data[2])
        finishdate = datetime.fromisoformat(class_data[3])
        meeting_date = datetime.fromisoformat(new_date)
        if meeting_date > startdate and meeting_date < finishdate:
            await db.update_meeting({'meeting_date': new_date}, meeting_id)
            tasks = asyncio.all_tasks()
            try:
                current_task = next(filter(lambda t: t.get_name() == f"{meeting_id} meeting_notif", tasks))
                current_task.cancel()
                if current_task in notif_tasks:
                    notif_tasks.discard(current_task)
            except:
                pass
            notif_tasks.add(asyncio.create_task(coro=notifications.meetings_notification_dispatcher(meeting_id, class_id), 
                            name=f"{meeting_id} meeting_notif"))
            data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                        admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
            await showMeetingInfo(data, message.chat.id, msg_id, 'edited_current_date')
        else:
            data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                        admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
            await showMeetingInfo(data, message.chat.id, msg_id, 'wrong_current_date_potok')
@router.message(AdminPanel.choose_next_meeting_date)
async def wrong_meeting_date(message, state):
    admin_data = await state.get_data() 
    data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                    admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
    if admin_data['current_meeting_id'] == 'new':
        await showMeetingInfo(data, message.chat.id, admin_data['meetings_menu_msg'], 'wrong_new_date')
    else:
        await showMeetingInfo(data, message.chat.id, admin_data['meetings_menu_msg'], 'wrong_current_date')
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)

    
@router.message(AdminPanel.choose_next_meeting_link, F.entities[0].type.in_({'url'}))
async def meeting_link_change(message, state):
    await state.set_state(None)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    offset = message.entities[0].offset
    length = message.entities[0].length
    new_link = message.text[offset:offset+length]
    admin_data = await state.get_data()
    msg_id = admin_data['meetings_menu_msg']
    meeting_id = admin_data['current_meeting_id']
    if meeting_id == 'new':
        await state.update_data(new_meeting_link=new_link)
        admin_data = await state.get_data()
        data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                    admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
        await showMeetingInfo(data, message.chat.id, msg_id, 'create_new')
    else:
        await db.update_meeting({'link': new_link}, meeting_id)
        data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                    admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
        await showMeetingInfo(data, message.chat.id, msg_id, 'edited_current_link')
@router.message(AdminPanel.choose_next_meeting_link)
async def wrong_meeting_link(message, state):
    admin_data = await state.get_data() 
    data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                    admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))
    if admin_data['current_meeting_id'] == 'new':
        await showMeetingInfo(data, message.chat.id, admin_data['meetings_menu_msg'], 'wrong_new_link')
    else:
        await showMeetingInfo(data, message.chat.id, admin_data['meetings_menu_msg'], 'wrong_current_link')
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)


async def getInfoToPaste(class_id: int | str):
    class_data = await db.get_class(class_id)
    return dict(zip(['class_id', 'name', 'start_date', 'finish_date', 'is_present'], class_data))

async def checkCurrentDates(startdate: str, finishdate: str):
    startdate = datetime.fromisoformat(startdate)
    finishdate = datetime.fromisoformat(finishdate)
    if finishdate < datetime.now():
        return 'move_to_old'
    if finishdate < startdate:
        return 'invalid_start_finish'
    if startdate + timedelta(days=30*config.maximum_months) > finishdate:
        return 'less_than_max'
    return 'ok'

# MAIL
@router.message(MailPanel.message_input, F.photo | F.document | F.audio | F.voice | F.text | F.video | F.video_note)
async def mail_message_input(message, state):
    text = message.text if message.text else message.caption
    if not text:
        text = ''
    result_dict = {'text': text}
    keyboard = keyboards.mailing_delete_message()
    if message.photo:
        result_dict['type'] = 'photo'
        result_dict['file_id'] = message.photo[-1].file_id
        try:
            await SendPhoto(chat_id=message.chat.id, photo=message.photo[-1].file_id, caption=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.audio:
        result_dict['type'] = 'audio'
        result_dict['file_id'] = message.audio.file_id
        try:
            await SendAudio(chat_id=message.chat.id, audio=message.audio.file_id, caption=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.document:
        result_dict['type'] = 'document'
        result_dict['file_id'] = message.document.file_id
        try:
            await SendDocument(chat_id=message.chat.id, document=message.document.file_id, caption=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.voice:
        result_dict['type'] = 'voice'
        result_dict['file_id'] = message.voice.file_id
        try:
            await SendVoice(chat_id=message.chat.id, voice=message.voice.file_id, caption=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.video:
        result_dict['type'] = 'video'
        result_dict['file_id'] = message.video.file_id
        try:
            await SendVideo(chat_id=message.chat.id, video=message.video.file_id, caption=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.video_note:
        result_dict['type'] = 'video_note'
        result_dict['file_id'] = message.video_note.file_id
        try:
            await SendVideoNote(chat_id=message.chat.id, video_note=message.video_note.file_id, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    elif message.text:
        result_dict['type'] = 'text'
        result_dict['file_id'] = None
        try:
            await message.answer(text=text, reply_markup=keyboard)
        except BaseException as e:
            await message.answer(f"Произошла ошибка при отправке сообщения:\n{e}")
            return
    
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    await state.update_data(mailing_msg_data=result_dict)
    admin_data = await state.get_data()
    await editMailInfo(message.chat.id, admin_data['mail_menu_msg'],
                       {'tarifs': admin_data['current_tarifs_mailing'], 'classes': admin_data['current_classes_mailing']},
                       'confirm_sending')
@router.message(MailPanel.message_input)
async def wrong_mailing_input(message, state):
    admin_data = await state.get_data()
    await editMailInfo(message.chat.id, admin_data['mail_menu_msg'],
                       {'tarifs': admin_data['current_tarifs_mailing'], 'classes': admin_data['current_classes_mailing']},
                       'wrong_sending')
        
        
        





# FILE INPUT
@router.message(FilePanel.file_input, F.document)
async def file_input(message, state):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    msg_id = admin_data['file_menu_msg']
    mode = admin_data['current_file_mode']
    file_id = admin_data['current_file_editing']
    document_id = message.document.file_id
    if mode == 'new':
        await db.create_file(file_id, document_id)
    else:
        await db.edit_file(file_id, document_id)
    await state.set_state(None)
    await state.update_data(current_file_editing=None, current_file_mode=None)
    await editFileInfo(message.chat.id, msg_id, f'success_adding {file_id}')
@router.message(FilePanel.file_input)
async def wrong_input(message, state):
    admin_data = await state.get_data()
    file_id = admin_data['current_file_editing']
    await editFileInfo(message.chat.id, admin_data['file_menu_msg'], f'wrong_input {file_id}')
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)




# CURRENT
@router.message(ClassPanel.edit_current_class_name, ((F.text.len() > 0) & (F.text.len() < 50)))
async def edit_current_name(message, state):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    new_name = message.text
    class_id = admin_data['current_class_editing']
    menu_msg = admin_data['class_menu_msg']
    await db.edit_class({'name': new_name}, class_id)
    await editShowClassInfo(await getInfoToPaste(class_id), 'success_edit_current_name', menu_msg, message.chat.id)
    await state.set_state(None)
@router.message(ClassPanel.edit_current_class_name)
async def wrong_edit_current_name(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    class_id = admin_data['current_class_editing']
    await editShowClassInfo(await getInfoToPaste(class_id), 'wrong_edit_current_name', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)

@router.message(ClassPanel.edit_current_class_startdate, F.text.regexp(config.date_regexp))
async def edit_current_startdate(message, state): 
    admin_data = await state.get_data()
    new_date = useless.datetoYYYYMMDD(message.text)
    class_id = admin_data['current_class_editing']
    menu_msg = admin_data['class_menu_msg']
    class_data = await db.get_class(class_id)
    result = await checkCurrentDates(new_date, class_data[3])
    if result == 'invalid_start_finish':
        await editShowClassInfo(await getInfoToPaste(class_id), 'wrong_edit_current_startdate', menu_msg, message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif result == 'less_than_max':
        await editShowClassInfo(await getInfoToPaste(class_id), 'start_date_less_than_max', menu_msg, message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif result == 'ok':
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await db.edit_class({'start_date': new_date}, class_id)
        tasks = asyncio.all_tasks()
        global notif_tasks
        try:
            current_task = next(filter(lambda t: t.get_name() == f"{class_id} class_notif", tasks))
            current_task.cancel()
            if current_task in notif_tasks:
                notif_tasks.discard(current_task)
        except:
            print('something went wrong')
        notif_tasks.add(asyncio.create_task(coro=notifications.class_notification_dispatcher(class_id), name=f"{class_id} class_notif"))
        current_sd = await redis.get(name='startdate')
        current_sd = datetime.fromisoformat(str(current_sd.decode()))
        if datetime.fromisoformat(new_date) > current_sd:
            await redis.set(name='startdate', value=str(new_date))
        await editShowClassInfo(await getInfoToPaste(class_id), 'success_edit_current_startdate', menu_msg, message.chat.id)
        await state.set_state(None)
@router.message(ClassPanel.edit_current_class_startdate)
async def wrong_edit_current_startdate(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    class_id = admin_data['current_class_editing']
    await editShowClassInfo(await getInfoToPaste(class_id), 'wrong_edit_current_startdate', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)

@router.message(ClassPanel.edit_current_class_finishdate, F.text.regexp(config.date_regexp))
async def edit_current_finishdate(message, state):
    admin_data = await state.get_data()
    new_date = useless.datetoYYYYMMDD(message.text)
    class_id = admin_data['current_class_editing']
    menu_msg = admin_data['class_menu_msg']
    class_data = await db.get_class(class_id)
    result = await checkCurrentDates(class_data[2], new_date)
    if result == 'move_to_old':
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.set_state(None)
        await state.update_data(confirming_finishdate=new_date)
        admin_data = await state.get_data()
        info = await getInfoToPaste(class_id)
        info['confirming_finishdate'] = new_date
        await editShowClassInfo(info, 'confirm_date_move_to_old', menu_msg, message.chat.id)
    elif result == 'invalid_start_finish':
        await editShowClassInfo(await getInfoToPaste(class_id), 'wrong_edit_current_finishdate', menu_msg, message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif result == 'less_than_max':
        await editShowClassInfo(await getInfoToPaste(class_id), 'finish_date_less_than_max', menu_msg, message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif result == 'ok':
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await db.edit_class({'finish_date': new_date}, class_id)
        tasks = asyncio.all_tasks()
        global notif_tasks
        try:
            current_task = next(filter(lambda t: t.get_name() == f"{class_id} class_notif", tasks))
            current_task.cancel()
            if current_task in notif_tasks:
                notif_tasks.discard(current_task)
        except:
            pass
        notif_tasks.add(asyncio.create_task(coro=notifications.class_notification_dispatcher(class_id), name=f"{class_id} class_notif"))
        await editShowClassInfo(await getInfoToPaste(class_id), 'success_edit_current_finishdate', menu_msg, message.chat.id)
        await state.set_state(None)
@router.message(ClassPanel.edit_current_class_finishdate)
async def wrong_edit_current_finishdate(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    class_id = admin_data['current_class_editing']
    await editShowClassInfo(await getInfoToPaste(class_id), 'wrong_edit_current_finishdate', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)



# NEW
@router.message(ClassPanel.edit_new_class_name, ((F.text.len() > 0) & (F.text.len() < 50)))
async def edit_new_name(message, state):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(None)
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    await state.update_data(new_class_name=message.text)
    admin_data = await state.get_data()
    await editShowClassInfo(admin_data, 'create', menu_msg, message.chat.id)
@router.message(ClassPanel.edit_new_class_name)
async def wrong_edit_new_name(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    await editShowClassInfo(admin_data, 'wrong_edit_new_name', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)


@router.message(ClassPanel.edit_new_class_startdate, F.text.regexp(config.date_regexp))
async def edit_current_startdate(message, state):
    admin_data = await state.get_data()
    new_date = useless.datetoYYYYMMDD(message.text)
    finish_date = admin_data['new_class_finishdate']
    if finish_date:
        availability = await checkCurrentDates(new_date, finish_date)
    else:
        availability = 'ok'
    if availability == 'ok':
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.set_state(None)
        await state.update_data(new_class_startdate=new_date)
        admin_data = await state.get_data()
        await editShowClassInfo(admin_data, 'create', admin_data['class_menu_msg'], message.chat.id)
    elif availability == 'invalid_start_finish':
        await editShowClassInfo(admin_data, 'wrong_edit_new_startdate', admin_data['class_menu_msg'], message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif availability == 'less_than_max':
        await editShowClassInfo(admin_data, 'wrong_new_startdate_less_max', admin_data['class_menu_msg'], message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
@router.message(ClassPanel.edit_new_class_startdate)
async def wrong_edit_new_startdate(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    await editShowClassInfo(admin_data, 'wrong_edit_new_startdate', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)


@router.message(ClassPanel.edit_new_class_finishdate, F.text.regexp(config.date_regexp))
async def edit_current_finishdate(message, state):
    
    admin_data = await state.get_data()
    new_date = useless.datetoYYYYMMDD(message.text)
    start_date = admin_data['new_class_startdate']
    if start_date:
        availability = await checkCurrentDates(start_date, new_date)
    else:
        if datetime.fromisoformat(new_date) > datetime.now():
            availability = 'ok'
        else:
            availability = 'invalid_start_finish'
    if availability == 'ok':
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
        await state.set_state(None)
        await state.update_data(new_class_finishdate=new_date)
        admin_data = await state.get_data()
        await editShowClassInfo(admin_data, 'create', admin_data['class_menu_msg'], message.chat.id)
    elif availability == 'invalid_start_finish' or availability == 'move_to_old':
        await editShowClassInfo(admin_data, 'wrong_edit_new_finishdate', admin_data['class_menu_msg'], message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    elif availability == 'less_than_max':
        await editShowClassInfo(admin_data, 'wrong_new_finishdate_less_max', admin_data['class_menu_msg'], message.chat.id)
        await sleep(2)
        await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    
@router.message(ClassPanel.edit_new_class_finishdate)
async def wrong_edit_new_finishdate(message, state):
    admin_data = await state.get_data()
    menu_msg = admin_data['class_menu_msg']
    await editShowClassInfo(admin_data, 'wrong_edit_new_finishdate', menu_msg, message.chat.id)
    await sleep(2)
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)


@router.message(Command("start"))
async def start(message):
    #global notif_tasks
    
    #from asyncbot import tasks
    #print("-----------tasks:---------------")
    #for task in tasks:
    #    print(tasks)
    #print("-----------notif_tasks:---------------")
    #for task in notif_tasks:
    #    print(task)
    #import tracemalloc
    #current, peak = tracemalloc.get_traced_memory()
    #print(f"Current memory usage is {current / 10**6}MB; Peak was {peak / 10**6}MB")
    #data = gc.collect()
    #print(f"unreachable objects: {data}")
    #current, peak = tracemalloc.get_traced_memory()
    #print(f"Current memory usage is {current / 10**6}MB; Peak was {peak / 10**6}MB")
    await message.answer('Вы являетесь администратором.\n' 
                        'Для доступа к управлению участниками воспользуйтесь командой /user_menu.\n'
                        'Для изменения информации о лекциях воспользуйтесь /lectures_menu.\n'
                        'Для редактирования потоков воспользуйтесь /class_menu.\n'
                        'Для добавления файлов, присылаемых после лекций, воспользуйтесь /file_menu.\n'
                        'Для создания рассылки воспользуйтесь /send_menu.\n'
                        'Для экспорта таблиц из БД воспользуйтесь /export.')

@router.message(Command("export"))
async def export(message):
    await message.answer(text='Выберите таблицу для экспорта.', reply_markup=keyboards.export())


@router.message(Command(commands='user_menu'))
async def user_menu(message, state: FSMContext):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    if 'user_menu_msg' in admin_data:
        if admin_data['user_menu_msg']:
            try:
                await DeleteMessage(chat_id=message.chat.id, message_id=admin_data['user_menu_msg'])
            except:
                pass
    msg = await message.answer(text='Меню управления пользователями.', reply_markup=keyboards.admin_user_menu_begin())
    await state.update_data(user_menu_msg=msg.message_id)

@router.message(Command(commands='lectures_menu'))
async def meetings_menu(message, state: FSMContext):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    if 'meetings_menu_msg' in admin_data:
        if admin_data['meetings_menu_msg']:
            try:
                await DeleteMessage(chat_id=message.chat.id, message_id=admin_data['meetings_menu_msg'])
            except:
                pass
    msg = await message.answer(text="Меню управления лекциями.", reply_markup=keyboards.admin_meetings_menu_begin())
    await state.update_data(meetings_menu_msg=msg.message_id, new_meeting_date=None, new_meeting_link=None,
                            current_meeting_class=None, current_meeting_id=None)
    
@router.message(Command(commands='class_menu'))
async def class_menu(message, state: FSMContext):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    if 'class_menu_msg' in admin_data:
        if admin_data['class_menu_msg']:
            try:
                await DeleteMessage(chat_id=message.chat.id, message_id=admin_data['class_menu_msg'])
            except:
                pass
    msg = await message.answer(text="Меню управления потоками.", reply_markup=keyboards.admin_class_menu_begin())
    await state.update_data(class_menu_msg=msg.message_id)

@router.message(Command(commands='file_menu'))
async def file_menu(message, state: FSMContext):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    if 'file_menu_msg' in admin_data:
        if admin_data['file_menu_msg']:
            try:
                await DeleteMessage(chat_id=message.chat.id, message_id=admin_data['file_menu_msg'])
            except:
                pass
    msg = await message.answer(text="Меню управления файлами.", reply_markup=keyboards.file_menu_start())
    await state.update_data(file_menu_msg=msg.message_id)

@router.message(Command(commands='send_menu'))
async def send(message, state):
    await DeleteMessage(chat_id=message.chat.id, message_id=message.message_id)
    admin_data = await state.get_data()
    if 'mail_menu_msg' in admin_data:
        if admin_data['mail_menu_msg']:
            try:
                await DeleteMessage(chat_id=message.chat.id, message_id=admin_data['mail_menu_msg'])
            except:
                pass
    msg = await message.answer(text="Меню создания рассылок.\n\nБот может послать: обычный текст либо 1 медиа-файл из следующего списка: "
                               "аудио, фото, документ, голосовое сообщение, видео, видео-кружок вместе с текстом, приложенным к нему (если доступно).\n"
                               "Также бот поддерживает HTML-разметку (например, теги).\n\n"
                               "<b>Выберите адресатов:</b>\n"
                               "(Всем пользователям - всем, кто когда-либо писал боту.)", parse_mode='HTML',
                               reply_markup=keyboards.mailing_start([]))
    await state.update_data(mail_menu_msg=msg.message_id, current_tarifs_mailing=None, 
                            current_classes_mailing=None, mailing_msg_data=None)

@router.callback_query(F.data.contains('choose_name '))
async def process_name_choose(call, state):
    try:
        user_id = int(call.data.split()[1])
        await state.update_data(current_id=user_id)
        user_data = await state.get_data()
        data = await db.get_user(user_id)
        await showAdminInfo(data, call.message.chat.id, user_id, user_data['user_menu_msg'], 'show_info')
        await state.set_state(None)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)

    

@router.callback_query(F.data.contains('export'))
async def export(call):
    try:
        if 'export ' in call.data:
            await SendChatAction(chat_id=call.message.chat.id, action='upload_document')
            now = datetime.timestamp(datetime.now())
            bd_num = int(call.data.split()[1])
            match bd_num:
                case 1:
                    bdname = 'users'
                    loc_name = 'Users'
                    title_row = ['ID пользователя', 'ФИО', 'Номер телефона', 'E-mail',
                                 'Тариф', 'Кол-во оплаченных месяцев', 'ID потока', 'Доступ', 'Статус пробного периода']
                case 2:
                    bdname = 'classes'
                    loc_name = 'Classes'
                    title_row = ['ID потока', 'Название', 'Дата начала', 'Дата конца', 'Статус']
                case 3:
                    bdname = 'meetings'
                    loc_name = 'Lectures'
                    title_row = ['ID лекции', 'ID потока', 'Дата', 'Ссылка', 'Статус']
        f = open(f"{bdname}.csv", "w", encoding='utf-8')
        csvWriter = csv.writer(f)
        data = await db.select_all(bdname)
        csvWriter.writerow(title_row)
        match bd_num:
            case 1:
                for row in data:
                    row = list(row)
                    row[7] = 'да' if row[7] == 1 else 'нет'
                    match row[8]:
                        case 'using':
                            row[8] = 'Пользуется сейчас'
                        case 'expired':
                            row[8] = 'Истёк'
                        case _:
                            row[8] = 'Не пользовался'
                    match row[4]:
                        case '1':
                            row[4] = 'Самостоятельный'
                        case '2':
                            row[4] = 'Хочу большего'
                        case _:
                            row[4] = 'Не выбран'
                    csvWriter.writerow(row)
            case 2:
                for row in data:
                    row = list(row)
                    row[4] = 'Еще идет' if row[4] == 1 else 'Закончился'
                    csvWriter.writerow(row)
            case 3:
                for row in data:
                    row = list(row)
                    row[4] = 'Предстоит' if row[4] == 1 else 'Закончилась'
                    csvWriter.writerow(row)
        f.close()
        from multiprocessing import Process
        #p = Process(target=create_xlsx, args=(bdname,loc_name, call.message.chat.id))
        #p.start()
        
        
        #p.join()
        #p.close()
        try:
            merge_all_to_a_book(glob.glob(f"{bdname}.csv"), f"{bdname}.xlsx")
        except BaseException as e:
            await AnswerCallbackQuery(callback_query_id=call.id, text=f'Failed merge\n{type(e)}: {e}', show_alert=True)
        await SendDocument(chat_id=call.message.chat.id,
                       document=FSInputFile(path=f"{bdname}.xlsx", 
                                            filename=f"{loc_name} BD export {datetime.today():%d-%m-%Y %H.%M.%S}.xlsx"))
        try:
            os.remove(f"{bdname}.csv")
            os.remove(f"{bdname}.xlsx")
        except BaseException as e:
            await AnswerCallbackQuery(callback_query_id=call.id, text=f'Failed remove\n{type(e)}: {e}', show_alert=True)
        return
        
    except BaseException as e:
        await AnswerCallbackQuery(callback_query_id=call.id, text='Что-то пошло не так.', show_alert=True)
        print(type(e), ': ', e, ' (export)')


async def editMailInfo(admin_id: int | str, msg_id: int | str, data: dict, mode: str):
    text = ("Меню создания рассылок.\n\nБот может послать: обычный текст либо 1 медиа-файл из следующего списка: "
            "аудио, фото, документ, голосовое сообщение, видео, видео-кружок вместе с текстом, приложенным к нему (если доступно).\n"
            "Также бот поддерживает HTML-разметку (например, теги).\n\n")


    if mode == 'casual' or mode == 'success_sending':
        if mode == 'success_sending':
            text += "<b>Ваше сообщение успешно отправлено адресатам.</b>\n\n"
        text += ("<b>Выберите адресатов:</b>\n"
            "(Всем пользователям - всем, кто когда-либо писал боту.)\n\n")
        keyboard = keyboards.mailing_start([])
    elif mode == 'to_all':
        text += "<b>Введите Ваше сообщение. Оно будет отправлено ВСЕМ пользователям, которые когда-либо писали боту.</b>"
        keyboard = keyboards.mailing_back_to_main()
    elif mode == 'tarifs_choose':
        cur_tarifs = data['tarifs']
        if cur_tarifs:
            text += "<b>Выбраны тарифы: </b>\n"
            i = 0
            for tarif in cur_tarifs:
                i += 1
                text += f"{i}. {useless.tarifName(tarif)}\n"
        else:
            text += "<b>Все тарифы убраны. </b>"
        keyboard = keyboards.mailing_start(cur_tarifs)
    elif mode == 'potok_choose':
        cur_tarifs = data['tarifs']
        text += "<b>Выбраны тарифы: </b>\n"
        i = 0
        for tarif in cur_tarifs:
            i += 1
            text += f"{i}. {useless.tarifName(tarif)}\n"
        
        
        if data['classes']:
            text += "\n<b>В данный момент выбраны потоки: </b>\n"
            
            i = 0
            for class_id in data['classes']:
                i += 1
                class_data = await db.get_class(class_id)
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
            
                
        
        classes_data = await db.get_present_classes()
        if classes_data:
            text += "\n<b>Выберите поток: </b>\n"
            i = 0
            for class_data in classes_data:
                i += 1
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
        else:
            text += "\n<b>Текущих потоков не найдено.</b>"
        keyboard = keyboards.mailing_choose_class(classes_data, data['classes'])
    elif mode == 'final_send':
        text += "<b>Выбраны тарифы:</b>\n"
        if not data['tarifs'] == 'ALL':
            i = 0
            for tarif in data['tarifs']:
                i += 1
                text += f"{i}. {useless.tarifName(tarif)}\n"
        else:
            text += "<b>ВСЕ</b>\n"
        
        text += "\n<b>Выбраны потоки:</b>\n"
        
        if data['classes'] == 'ALL':
            text += "<b>ВСЕ</b>\n"
        else:
            i = 0
            for class_id in data['classes']:
                i += 1
                class_data = await db.get_class(class_id)
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"

        text += "\n<b>Введите сообщение, которое будет отправлено выбранным пользователям.</b>"
        keyboard = keyboards.mailing_back_to_potok()
    elif mode == 'confirm_sending':
        if not data['tarifs'] == 'ALL_ALL':
            text += "<b>Выбраны тарифы:</b>\n"
            if not data['tarifs'] == 'ALL':
                i = 0
                for tarif in data['tarifs']:
                    i += 1
                    text += f"{i}. {useless.tarifName(tarif)}\n"
            else:
                text += "<b>ВСЕ</b>\n"
            
            text += "\n<b>Выбраны потоки:</b>\n"
            
            if data['classes'] == 'ALL':
                text += "<b>ВСЕ</b>\n"
            else:
                i = 0
                for class_id in data['classes']:
                    i += 1
                    class_data = await db.get_class(class_id)
                    text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
            keyboard = keyboards.mailing_confirm_send(False)
        else:
            text += "<b>Сообщение будет отправлено ВСЕМ пользователям, которые когда-либо писали боту.</b>\n"
            keyboard = keyboards.mailing_confirm_send(True)
        text += "\n<b>Ваше сообщение будет выглядеть следующим образом, подтвердите отправку (продолжайте отправлять, пока сообщение Вас не устроит)</b>"
    elif mode == 'wrong_sending':
        if not data['tarifs'] == 'ALL_ALL':
            text += "<b>Выбраны тарифы:</b>\n"
            if not data['tarifs'] == 'ALL':
                i = 0
                for tarif in data['tarifs']:
                    i += 1
                    text += f"{i}. {useless.tarifName(tarif)}\n"
            else:
                text += "<b>ВСЕ</b>\n"
            
            text += "\n<b>Выбраны потоки:</b>\n"
            
            if data['classes'] == 'ALL':
                text += "<b>ВСЕ</b>\n"
            else:
                i = 0
                for class_id in data['classes']:
                    i += 1
                    class_data = await db.get_class(class_id)
                    text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
            keyboard = keyboards.mailing_back_to_potok()
        else:
            text += "<b>Сообщение будет отправлено ВСЕМ пользователям, которые когда-либо писали боту.</b>\n"
            keyboard = keyboards.mailing_back_to_main()
        text += "\n<b>В сообщении не найдены перечисленные медиа-файлы либо текст.</b>"
        
    try:
        await EditMessageText(text=text, chat_id=admin_id, message_id=msg_id, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)
        

@router.callback_query(F.data.contains('mailing'))
async def call_mailing(call, state):
    try:
        admin_data = await state.get_data()
        if call.data == 'mailing_all':
            await state.update_data(current_tarifs_mailing='ALL_ALL')
            await state.set_state(MailPanel.message_input)
            await editMailInfo(call.message.chat.id, call.message.message_id, {}, 'to_all')
        elif 'mailing_add_' in call.data:
            tarif = call.data.split('_')[2]
            cur_tarifs = admin_data['current_tarifs_mailing']
            if cur_tarifs:
                cur_tarifs.append(tarif)
            else:
                cur_tarifs = [tarif]
            await state.update_data(current_tarifs_mailing=cur_tarifs)
            await editMailInfo(call.message.chat.id, call.message.message_id, {'tarifs': cur_tarifs}, 'tarifs_choose')
        elif 'mailing_del_' in call.data:
            tarif = call.data.split('_')[2]
            cur_tarifs = admin_data['current_tarifs_mailing']
            cur_tarifs.remove(tarif)
            await state.update_data(current_tarifs_mailing=cur_tarifs)
            await editMailInfo(call.message.chat.id, call.message.message_id, {'tarifs': cur_tarifs}, 'tarifs_choose')
        elif call.data == 'mailing_to_potok':
            await state.set_state(None)
            await state.update_data(mailing_msg_data=None)
            if admin_data['current_classes_mailing'] == 'ALL':
                await state.update_data(current_classes_mailing=None)
                admin_data['current_classes_mailing'] = None
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': admin_data['current_classes_mailing']}, 'potok_choose')
        elif call.data == 'mailing_to_main':
            await state.set_state(None)
            await state.update_data(current_classes_mailing=None)
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': None}, 'tarifs_choose')
        elif call.data == 'mailing_to_main_all':
            await state.set_state(None)
            await state.update_data(current_tarifs_mailing=None, mailing_msg_data=None)
            await editMailInfo(call.message.chat.id, call.message.message_id, {}, 'casual')
        elif 'mailing_class_add_' in call.data:
            class_id = int(call.data.split('_')[3])
            cur_classes = admin_data['current_classes_mailing']
            if cur_classes:
                cur_classes.append(class_id)
            else:
                cur_classes = [class_id]
            await state.update_data(current_classes_mailing=cur_classes)
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': cur_classes}, 'potok_choose')
        elif 'mailing_class_del_' in call.data:
            class_id = int(call.data.split('_')[3])
            cur_classes = admin_data['current_classes_mailing']
            cur_classes.remove(class_id)
            await state.update_data(current_classes_mailing=cur_classes)
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': cur_classes}, 'potok_choose')
        elif call.data == 'mailing_class_all':
            await state.set_state(MailPanel.message_input)
            await state.update_data(current_classes_mailing='ALL')
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': 'ALL'}, 'final_send')
        elif call.data == 'mailing_final_send':
            await state.set_state(MailPanel.message_input)
            await editMailInfo(call.message.chat.id, call.message.message_id, 
                            {'tarifs': admin_data['current_tarifs_mailing'], 'classes': admin_data['current_classes_mailing']}, 'final_send')
        elif call.data == 'mailing_confirm_send':
            await state.set_state(None)
            await state.update_data(current_tarifs_mailing=None, current_classes_mailing=None, mailing_msg_data=None)
            await editMailInfo(call.message.chat.id, call.message.message_id, {}, 'success_sending')
            all_all = False
            if admin_data['current_tarifs_mailing'] == 'ALL_ALL':
                all_all = True
                tarifs = []
                classes = []
            else:
                tarifs = admin_data['current_tarifs_mailing']
                classes = admin_data['current_classes_mailing']
            user_ids = await db.get_userids_with_params(tarifs, classes, all_all)
            doc_type = admin_data['mailing_msg_data']['type']
            text = admin_data['mailing_msg_data']['text']
            file_id = admin_data['mailing_msg_data']['file_id']
            for user_data in user_ids:
                user_id = user_data[0]
                match doc_type:
                    case 'photo':
                        try:
                            await SendPhoto(chat_id=user_id, photo=file_id, caption=text)
                        except:
                            pass
                    case 'audio':
                        try:
                            await SendAudio(chat_id=user_id, audio=file_id, caption=text)
                        except:
                            pass
                    case 'document':
                        try:
                            await SendDocument(chat_id=user_id, document=file_id, caption=text)
                        except:
                            pass
                    case 'voice':
                        try:
                            await SendVoice(chat_id=user_id, voice=file_id, caption=text)
                        except:
                            pass
                    case 'video':
                        try:
                            await SendVideo(chat_id=user_id, video=file_id, caption=text)
                        except:
                            pass
                    case 'video_note':
                        try:
                            await SendVideoNote(chat_id=user_id, video_note=file_id, caption=text)
                        except:
                            pass
                    case 'text':
                        try:
                            await SendMessage(chat_id=user_id, text=text)
                        except:
                            pass
                    case _:
                        print(f'unknown type {doc_type}')
                await sleep(1)
        elif call.data == 'mailing_close':
            await state.update_data(mail_menu_msg=None)
            await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)




async def editFileInfo(admin_id, msgid, mode):
    text = "Меню управления файлами.\n\n"

    if mode == 'show':
        text += "Файлы в БД:\n"
        file_dict = {}
        for i in range(1, 20):
            file_dict[i] = '<b>нет</b>'
        files_data = await db.get_all_files()
        for file_data in files_data:
            file_dict[file_data[0]] = 'есть'
        for i in range(1, 20):
            text += f"{i} - {file_dict[i]}\n"
        keyboard = keyboards.show_files(file_dict)
    elif mode == 'main':
        keyboard = keyboards.file_menu_start()
    elif mode == 'choose to changedel':
        file_dict = {}
        for i in range(1, 20):
            file_dict[i] = '<b>нет</b>'
        files_data = await db.get_all_files()
        for file_data in files_data:
            file_dict[file_data[0]] = 'есть'
        for i in range(1, 20):
            text += f"{i} - {file_dict[i]}\n"
        text += "\n<b>Выберите файл, который нужно изменить: </b>"
        keyboard = keyboards.change_delete_files()
    elif 'choose_option ' in mode:
        file_num = mode.split()[1]
        file_data = await db.get_file(file_num)
        if file_data:
            a = 'есть в БД'
            exists = True
        else:
            a = 'нет в БД'
            exists = False
        text += f"<b>Выбран файл {file_num} ({a}).\nВыберите действие: </b>"
        keyboard = keyboards.file_options(file_num, exists)
    elif 'input_file ' in mode:
        file_num = mode.split()[1]
        text += f"<b>Отправьте файл который будет записан под номером {file_num}.</b>"
        keyboard = keyboards.back_out_of_file_options(file_num)
    elif 'delete_try ' in mode:
        file_num = mode.split()[1]
        text += f"<b>Вы действительно хотите удалить {file_num}?</b>"
        keyboard = keyboards.file_deleting(file_num)
    elif 'after_delete ' in mode:
        file_num = mode.split()[1]
        text += f"<b>Файл {file_num} успешно удалён.</b>"
        keyboard = keyboards.change_delete_files()
    elif 'wrong_input ' in mode:
        file_num = mode.split()[1]
        text += f"<b>Отправьте файл который будет записан под номером {file_num}.</b>\n"
        text += "<b>Нет файла в сообщении.</b>\n"
        keyboard = keyboards.back_out_of_file_options(file_num)
    elif 'success_adding ' in mode:
        file_num = mode.split()[1]
        text += f"<b>Файл под номером {file_num} записан.</b>"
        keyboard = keyboards.file_menu_start()

    try:
        await EditMessageText(text=text, chat_id=admin_id, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)
    
@router.callback_query(F.data.contains('file'))
async def call_file(call, state):
    try:
        if call.data == 'file show':
            await editFileInfo(call.message.chat.id, call.message.message_id, 'show')
        elif call.data == 'file back to main':
            await editFileInfo(call.message.chat.id, call.message.message_id, 'main')
        elif 'show_file ' in call.data:
            file_num = int(call.data.split()[1])
            document_id = await db.get_file(file_num)
            try:
                await SendDocument(chat_id=call.message.chat.id, document=document_id[0][1])
            except TelegramBadRequest as e:
                if 'wrong remote file identifier' in e.message:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Произошла ошибка при отправке. Возможно файл устарел, загрузите новый.", show_alert=True)
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Произошла неизвестная ошибка. Попробуйте загрузить файл заново.", show_alert=True)
                await db.delete_file(file_num)
                await editFileInfo(call.message.chat.id, call.message.message_id, 'show')
                return 
        elif call.data == 'file changedelete' or call.data == 'file back to changedel':
            await editFileInfo(call.message.chat.id, call.message.message_id, 'choose to changedel')
        elif 'file_choose ' in call.data or 'file_back_to_options ' in call.data:
            if 'file_back_to_options ' in call.data:
                await state.set_state(None)
                await state.update_data(current_file_editing=None)
            file_num = int(call.data.split()[1])
            await editFileInfo(call.message.chat.id, call.message.message_id, f'choose_option {file_num}')
        elif 'add_file ' in call.data or 'change_file ' in call.data:
            file_num = int(call.data.split()[1])
            await state.set_state(FilePanel.file_input)
            mode = 'new' if 'add_file ' in call.data else 'old'
            await state.update_data(current_file_editing=file_num, current_file_mode=mode)
            await editFileInfo(call.message.chat.id, call.message.message_id, f'input_file {file_num}')  
        elif 'delete_file_try ' in call.data:
            file_num = int(call.data.split()[1])
            file_data = await db.get_file(file_num)
            if file_data:
                await editFileInfo(call.message.chat.id, call.message.message_id, f'delete_try {file_num}')
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Файла нет в БД.", show_alert=True)
        elif 'delete_file ' in call.data:
            file_num = int(call.data.split()[1])
            await db.delete_file(file_num)
            await editFileInfo(call.message.chat.id, call.message.message_id, f'after_delete {file_num}')
        elif call.data == 'file close':
            await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await state.update_data(file_menu_msg=None)
    except BaseException as e:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)



async def editPdfInfo(admin_id, class_id, num, msgid, mode):
    class_data = await db.get_class(class_id)
    class_name = class_data[1]

    if mode == 'finish':
        text = f"Файл {num} успешно отправлен всем пользователям потока {class_name} с тарифом «{useless.tarifName('2')}»."
        await EditMessageText(text=text, chat_id=admin_id, message_id=msgid, parse_mode='HTML', reply_markup=None)
        return

    text = (f"У потока {class_name} началась лекция.\n"
            f"Подтвердите отправку {num}.pdf пользователям.")

    if mode == 'change':
        text += "\n\n<b>Выберите номер файла который нужно отправить: </b>"
        keyboard = keyboards.change_pdf_meeting(class_id, num) 
    elif mode == 'main':
        keyboard = keyboards.pdf_after_meeting(class_id, num)
    elif mode == 'after_change':
        text += f"\n\n<b>Смена файла на {num} прошла успешно.</b>"
        keyboard = keyboards.pdf_after_meeting(class_id, num)
    try:
        await EditMessageText(text=text, chat_id=admin_id, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)

@router.callback_query(F.data.contains('pdf'))
async def call_pdf(call):
    try:
        num = int(call.data.split()[1])
        class_id = int(call.data.split()[2])
        if 'send_pdf ' in call.data:
            file_data = await db.get_file(num)
            if file_data:
                await editPdfInfo(call.message.chat.id, class_id, num, call.message.message_id, 'finish')
                users_data  = await db.get_class_users_with_tarif(class_id, [2])
                free_data = await db.get_class_free_users(class_id)
                for user_data in users_data:
                    try:
                        await SendDocument(chat_id=user_data[0], document=file_data[0][1], caption="PDF-материал по пройденной лекции.")
                    except TelegramBadRequest as e:
                        if 'wrong remote file identifier' in e.message:
                            class_data = await db.get_class(class_id)
                            for admin_id in config.admins:
                                await SendMessage(chat_id=admin_id, text=f"Файл №{num} не удалось отправить потоку {class_data[1]}. Скорее всего, "
                                                  "он больше не доступен на серверах Telegram.\nЗапись о файле удалена из БД. Загрузите файл заново, а также отправьте его через"
                                                  " /send_menu пользователям в потоке.")
                            await db.delete_file(num)
                            return
                        await sleep(5)
                    await sleep(1)
                for user_data in free_data:
                    try:
                        await SendDocument(chat_id=user_data[0], document=file_data[0][1], caption="PDF-материал по пройденной лекции.")
                    except TelegramBadRequest as e:
                        if 'wrong remote file identifier' in e.message:
                            class_data = await db.get_class(class_id)
                            for admin_id in config.admins:
                                await SendMessage(chat_id=admin_id, text=f"Файл №{num} не удалось отправить потоку {class_data[1]}. Скорее всего, "
                                                  "он больше не доступен на серверах Telegram.\nЗапись о файле удалена из БД. Загрузите файл заново, а также отправьте его через"
                                                  " /send_menu пользователям в потоке.")
                            await db.delete_file(num)
                            return
                        await sleep(5)
                    await sleep(1)
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Файла нет в БД!", show_alert=True)
        elif 'change_pdf ' in call.data:
            await editPdfInfo(call.message.chat.id, class_id, num, call.message.message_id, 'change')
        elif 'pdf_back ' in call.data:
            await editPdfInfo(call.message.chat.id, class_id, num, call.message.message_id, 'main')
        elif 'conf_pdf ' in call.data:
            file_data = await db.get_file(num)
            if file_data:
                await editPdfInfo(call.message.chat.id, class_id, num, call.message.message_id, 'after_change')
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Файла нет в БД!", show_alert=True)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)
    



async def editAdminInfo(admin_id, user_data, user_id, message_id, mode):
    if not user_data['tarif']:
        user_data['tarif'] = "Не выбран"
    else:
        tarif = useless.tarifName(user_data['tarif'])
    match user_data['free_expiration_date']:
        case '0':
            free_status = 'Не пользовался'
        case 'expired':
            free_status = 'Истёк'
        case 'using':
            free_status = 'Пользуется сейчас'
    if user_data['class_id'] == 0:
        class_info = 'Не выбран'
    else:
        class_data = await db.get_class(user_data['class_id'])
        class_info = f"{class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})"
    
    
    text = (f"Поступил запрос от пользователя с ID: {user_id}.\nФИО: {user_data['name']}.\n"
            f"Номер телефона: {user_data['phone']}.\nЭлектронная почта: {user_data['email']}.\n"
            f"Тариф: {tarif}.\nКоличество оплаченных месяцев: {user_data['paid_months']}.\n"
            f"Поток: {class_info}.\nСтатус пробного периода: {free_status}.\n\n")
    
    
    if mode == 'casual':
        keyboard = keyboards.KBBuilder(user_id)

    elif mode == 'confirm_access':
        text += "<b>Доступ к курсу открыт.</b>"
        keyboard = None

    elif mode == 'cancel':
        text += "<b>Запрос отклонён.</b>"
        keyboard = None
    
    elif mode == 'choose_class':
        
        classes_data = await db.get_present_classes()
        if classes_data:
            text += "<b>Выберите поток, к которому пользователь принадлежит:\n"
            i = 0
            for class_data in classes_data:
                i += 1
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n"
            text += "</b>"
            keyboard = keyboards.admin_request_class_choose(classes_data, user_id)
        else:
            text += "<b>Сейчас нет действующих потоков, сначала добавьте их с помощью /class_menu.</b>"
            keyboard = keyboards.KBBuilder(user_id)

    elif mode == 'insert_months':
        text += "<b>Выберите количество месяцев, оплаченных пользователем.</b>"
        keyboard = keyboards.admin_months_choose(user_id)
    
  
    try:
        await EditMessageText(chat_id=admin_id, text=text, message_id=message_id, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)

@router.callback_query(F.data.contains('adm'))
async def call_with_adm(call, state):
    try:
        admin_data = await state.get_data()
        if not 'request_dict' in admin_data:
            await state.update_data(request_dict={})
            admin_data = await state.get_data()
        user_id = int(call.data.split()[1])
        if not str(user_id) in admin_data['request_dict']:
            d = admin_data['request_dict']
            user_data = await db.get_user(user_id)
            d[user_id] = {'name': user_data[1], 'phone': user_data[2], 'email': user_data[3], 'tarif': user_data[4], 
                        'paid_months': user_data[5], 'class_id': user_data[6], 'access': user_data[7], 
                        'free_expiration_date': user_data[8], 'curr_adm_msg': call.message.message_id}
            await state.update_data(request_dict=d)
        admin_data = await state.get_data()
        user_data = admin_data['request_dict'][str(user_id)]
        changed = False
        finish = False
        
        if 'cancel' in call.data:
            user_data = await db.get_user(user_id)
            user_data = dict(zip(('name', 'phone', 'email', 'tarif', 'paid_months', 'class_id', 'access', 'free_expiration_date'), 
                        user_data[1:]))
            try:
                await SendMessage(chat_id=user_id, text=f"Ваш запрос отклонён.\nПроверьте правильность введённых данных и"
                            " оплачен ли курс.\nИзменить данные можно с помощью команды /changeinfo.\nПовторный запрос можно будет отправить через "
                            f"{config.tryAgainTimeout//60} минут.", reply_markup=keyboards.reject_access_adm(user_data['free_expiration_date']))
            except:
                pass
            await state.update_data(current_adm_id=None)
            finish = True
            await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'cancel')
        
        elif 'tar' in call.data:
            tarif_num = call.data.split()[0][-1]
            if user_data['tarif'] != tarif_num:
                user_data['tarif'] = tarif_num
                user_data['tarif'] = tarif_num
                changed = True
                await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'casual')
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Выбран тот же тариф.")
        
        elif 'choose_payment' in call.data:
            await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'insert_months')
        
        elif 'months' in call.data:
            months = call.data.split()[2]
            if months == 'plus_one':
                months = user_data['paid_months'] + 1
            months = int(months)
            if months != user_data['paid_months']:
                user_data['paid_months'] = months
                user_data['paid_months'] = months
                changed = True
                await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'casual')
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Количество месяцев совпадает с предыдущим.")

        elif 'choose_class' in call.data:
            await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'choose_class')
        
        elif 'class' in call.data:
            class_id = int(call.data.split()[2])
            if class_id != user_data['class_id']:
                user_data['class_id'] = class_id
                changed = True
                await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'casual')
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Выбранный поток совпадает с предыдущим.")
        
        elif 'confirm' in call.data:

            
            if user_data['tarif'] != 'Не выбран' and user_data['class_id'] != 0 and user_data['paid_months'] != 0:
                user_data['access'] = 1
                changed = True
                finish = True
                await db.update_user(data=user_data, user_id=user_id, mode='user_status_update')
                await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'confirm_access')
                try:
                    await SendMessage(chat_id=user_id, text='Вам открыт доступ к курсу.')
                except:
                    pass
                if user_data['tarif'] == '1':
                    await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_1.png"), 
                                caption="Описание тарифа «Самостоятельный»", reply_markup=keyboards.reply(False))
                elif user_data['tarif'] == '2':
                    await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_2.png"), 
                                caption="Описание тарифа «Хочу большего»", reply_markup=keyboards.reply(True))
                
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Заполнены не все поля.", show_alert=True)
        
        
                    
        
        elif 'abandon_change' in call.data:
            await editAdminInfo(call.message.chat.id, user_data, user_id, call.message.message_id, 'casual')
            await state.set_state(None)
        
        
        if changed or finish:
            data = await state.get_data()
            d = data['request_dict']
            if changed:
                d[str(user_id)] = user_data
            if finish:
                d.pop(str(user_id))
            await state.update_data(request_dict=d)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)



async def editShowClassInfo(data: dict, mode: str, msg_id: int, admin_id: int):
    text = "Меню управления потоками.\n\n"

    namechange = "<b>Введите название потока.</b>"
    startdatechange = "<b>Введите дату начала потока в формате ДД-ММ-ГГГГ.</b>"
    finishdatechange = "<b>Введите дату конца потока в формате ДД-ММ-ГГГГ.</b>"


    if mode == 'casual':
        keyboard = keyboards.admin_class_menu_begin()
    elif mode == 'after_deleting':
        text += "<b>Поток успешно удалён.</b>"
        keyboard = keyboards.admin_class_menu_begin()
    elif mode == 'create':
        text += "<b>Создание нового потока.</b>\n"
        name = data['new_class_name'] if data['new_class_name'] else 'Не выбрано'
        start_date = useless.dateToStr(datetime.fromisoformat(data['new_class_startdate'])) if data['new_class_startdate'] else 'Не выбрана'
        finish_date = useless.dateToStr(datetime.fromisoformat(data['new_class_finishdate'])) if data['new_class_finishdate'] else 'Не выбрана'
        text += (f"Название: {name}\nДата начала: {start_date}\n"
                f"Дата конца: {finish_date}")
        keyboard = keyboards.admin_class_menu_create()
    elif mode == 'show_current':
        present_classes = await db.get_present_classes()
        if present_classes:
            text += "<b>Выберите поток для редактирования:</b>\n\n"
            i = 0
            for class_data in present_classes:
                i += 1
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n"
            keyboard = keyboards.admin_class_choose_present_class(present_classes)
        else:
            text += "<b>Действующих потоков не найдено.</b>"
            keyboard = keyboards.admin_class_pure_back_to_menu()
    elif mode == 'edit_current':
        text += "<b>Редактирование текущего потока.</b>\n"
        text += (f"Название: {data['name']}\nДата начала: {useless.dateToDDMMYYYY(data['start_date'])}\n"
                f"Дата конца: {useless.dateToDDMMYYYY(data['finish_date'])}")
        keyboard = keyboards.admin_class_edit_present()
    elif 'editing_current_' in mode:
        text += "<b>Редактирование текущего потока.</b>\n"
        text += (f"Название: {data['name']}\nДата начала: {useless.dateToDDMMYYYY(data['start_date'])}\n"
                f"Дата конца: {useless.dateToDDMMYYYY(data['finish_date'])}\n")
        changing = mode.split('_')[2]
        if changing == 'name':
            text += namechange
        elif changing == 'startdate':
            text += startdatechange
        elif changing == 'finishdate':
            text += finishdatechange
        keyboard = keyboards.admin_class_back_to_current()
    elif 'editing_new_' in mode:
        text += "<b>Создание нового потока.</b>\n"
        name = data['new_class_name'] if data['new_class_name'] else 'Не выбрано'
        start_date = useless.dateToStr(datetime.fromisoformat(data['new_class_startdate'])) if data['new_class_startdate'] else 'Не выбрана'
        finish_date = useless.dateToStr(datetime.fromisoformat(data['new_class_finishdate'])) if data['new_class_finishdate'] else 'Не выбрана'
        text += (f"Название: {name}\nДата начала: {start_date}\n"
                f"Дата конца: {finish_date}\n")
        changing = mode.split('_')[2]
        if changing == 'name':
            text += namechange
        elif changing == 'startdate':
            text += startdatechange
        elif changing == 'finishdate':
            text += finishdatechange
        keyboard = keyboards.admin_class_back_to_new()
    elif mode == 'show_old':
        classes_data = await db.get_old_classes()
        if classes_data:
            text += "<b>Просмотр старых потоков.</b>\n"
            i = 0
            for class_data in classes_data:
                i += 1
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n"
        else:
            text += "<b>Старых потоков не найдено.</b>"
        
        keyboard = keyboards.admin_class_pure_back_to_menu()
    elif 'success_edit_current_' in mode or 'wrong_edit_current_' in mode or mode == 'try_to_delete'\
            or mode == 'show_users' or 'date_less_than_max' in mode:
        
        text += "<b>Редактирование текущего потока.</b>\n"
        text += (f"Название: {data['name']}\nДата начала: {useless.dateToDDMMYYYY(data['start_date'])}\n"
                f"Дата конца: {useless.dateToDDMMYYYY(data['finish_date'])}\n")
        if 'success' in mode:
            changed = mode.split('_')[3]
            if changed == 'name':
                text += "<b>Название успешно изменено.</b>"
            elif changed == 'startdate':
                text += "<b>Дата начала успешно изменена.</b>"
            elif changed == 'finishdate':
                text += "<b>Дата конца успешно изменена.</b>"
            keyboard = keyboards.admin_class_edit_present()
        elif 'wrong' in mode:
            changed = mode.split('_')[3]
            if changed == 'name':
                text += "<b>Неправильно введено название.</b>\n"
                text += namechange
            elif changed == 'startdate':
                text += "<b>Неправильно введена дата.</b>\n"
                text += startdatechange
            elif changed == 'finishdate':
                text += "<b>Неправильно введена дата.</b>\n"
                text += finishdatechange
            keyboard = keyboards.admin_class_back_to_current()
        elif mode == 'try_to_delete':
            text += "<b>Вы действительно хотите удалить поток? Удалять можно только потоки, в которых нет пользователей.</b>"
            keyboard = keyboards.admin_class_confirm_deleting()
        elif mode == 'show_users':
            class_id = data['class_id']
            users_data = await db.get_class_users(class_id)
            if users_data:
                text += "\nСписок пользователей в потоке:\n"
                i = 0
                for user_data in users_data:
                    i += 1
                    text += f"{i}. {user_data[0]}\n"
            else:
                text += "\n<b>Пользователй в потоке не найдено.</b>"
            keyboard = keyboards.admin_class_back_to_current2()
        elif '_date_less_than_max' in mode:
            date = mode.split('_')[0]
            if date == 'start':
                text += f"<b>Невозможно изменить начальную дату так, что длительность потока составляет менее {config.maximum_months} месяцев.</b>\n"
                text += startdatechange
            elif date == 'finish':
                text += f"<b>Невозможно изменить конечную дату так, что длительность потока составляет менее {config.maximum_months} месяцев.</b>\n"
                text += finishdatechange
            keyboard = keyboards.admin_class_back_to_current()
        
    elif mode == 'confirm_date_move_to_old':
        text += "<b>Редактирование текущего потока.</b>\n"
        text += (f"Название: {data['name']}\nДата начала: {useless.dateToDDMMYYYY(data['start_date'])}\n"
                f"Дата конца: {useless.dateToDDMMYYYY(data['finish_date'])}\n")
        text += (f"<b>Введённая дата завершения ({useless.dateToStr(datetime.fromisoformat(data['confirming_finishdate']))}) "
                "автоматически завершит поток, подтвердите действие.</b>")
        keyboard = keyboards.confirm_move_to_old()
    
    elif mode == 'after_moving_to_old':
        text += "<b>Текущий поток завершён и больше недоступен для редактирования. Его можно найти во вкладке «Старые потоки».</b>"
        keyboard = keyboards.admin_class_menu_begin()

    elif 'wrong_edit_new_' in mode or mode == 'wrong_new_startdate_less_max' or mode == 'wrong_new_finishdate_less_max':
        text += "<b>Создание нового потока.</b>\n"
        name = data['new_class_name'] if data['new_class_name'] else 'Не выбрано'
        start_date = useless.dateToStr(datetime.fromisoformat(data['new_class_startdate'])) if data['new_class_startdate'] else 'Не выбрана'
        finish_date = useless.dateToStr(datetime.fromisoformat(data['new_class_finishdate'])) if data['new_class_finishdate'] else 'Не выбрана'
        text += (f"Название: {name}\nДата начала: {start_date}\n"
                f"Дата конца: {finish_date}\n")
        if 'wrong_edit_new_' in mode:
            changed = mode.split('_')[3]
            if changed == 'name':
                text += "<b>Неправильно введено название.</b>\n"
                text += namechange
            elif changed == 'startdate':
                text += "<b>Дата начала введена неверно или больше даты окончания.</b>\n"
                text += startdatechange
            elif changed == 'finishdate':
                text += "<b>Дата окончания введена неверно, уже прошла или меньше даты начала.</b>\n"
                text += finishdatechange
        elif mode == 'wrong_new_startdate_less_max':
            text += f"<b>Невозможно задать начальную дату так, что длительность потока составляет менее {config.maximum_months} месяцев.</b>\n"
            text += startdatechange
        elif mode == 'wrong_new_finishdate_less_max':
            text += f"<b>Невозможно задать конечную дату так, что длительность потока составляет менее {config.maximum_months} месяцев.</b>\n"
            text += finishdatechange
        keyboard = keyboards.admin_class_back_to_new()

    elif mode == 'after_new_create':
        text += "<b>Поток успешно создан. Вы можете его отредактировать с помощью кнопки ниже.</b>"
        keyboard = keyboards.admin_class_menu_begin()
    
    elif mode == 'finish':
        keyboard = None




    try:
        await EditMessageText(text=text, chat_id=admin_id, message_id=msg_id, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)

@router.callback_query(F.data.contains('class'))
async def call_with_class(call, state):
    try:
        global notif_tasks
        # кнопка создать новый поток & кнопка назад из изменения чего-либо в новом потоке
        if call.data == 'create new class' or call.data == 'back_to_new_class':
            admin_data = await state.get_data()
            if not 'new_class_name' in admin_data:
                await state.update_data(new_class_name=None, new_class_startdate=None, new_class_finishdate=None)
                admin_data = await state.get_data()
            await state.set_state(None)
            await editShowClassInfo(admin_data, 'create', call.message.message_id, call.message.chat.id)
        
        # кнопка редактировать текущие потоки 
        elif call.data == 'edit present class' or call.data == 'return_to_show_current_classes':
            await state.update_data(current_class_editing=None)
            await editShowClassInfo({}, 'show_current', call.message.message_id, call.message.chat.id)
        
        # кнопка выбора текущего потока & кнопка назад из редактирования данных потока
        elif 'edit_present_class' in call.data or call.data == 'back_to_show_current_class':
            await state.set_state(None)
            if 'edit_present_class' in call.data:
                class_id = int(call.data.split()[1])
                await state.update_data(current_class_editing=class_id)
                class_data = await db.get_class(class_id)
            else:
                admin_data = await state.get_data()
                class_data = await db.get_class(admin_data['current_class_editing'])
            await editShowClassInfo({'name': class_data[1], 'start_date': class_data[2], 'finish_date': class_data[3]}, 
                                    'edit_current', call.message.message_id, call.message.chat.id)
        
        # изменения напрямую в текущем потоке
        elif 'current_class_edit' in call.data:
            mode = call.data.split('_')[3]
            if mode == 'name':
                await state.set_state(ClassPanel.edit_current_class_name)
            elif mode == 'startdate':
                await state.set_state(ClassPanel.edit_current_class_startdate)
            elif mode == 'finishdate':
                await state.set_state(ClassPanel.edit_current_class_finishdate)
            admin_data = await state.get_data()
            class_data = await db.get_class(admin_data['current_class_editing'])
            await editShowClassInfo({'name': class_data[1], 'start_date': class_data[2], 'finish_date': class_data[3]}, 
                                    f'editing_current_{mode}', call.message.message_id, call.message.chat.id)

        # просмотр пользователей потока
        elif call.data == 'current_class_show_users':
            admin_data = await state.get_data()
            class_data = await db.get_class(admin_data['current_class_editing'])
            users_data = await db.get_class_users(admin_data['current_class_editing'])
            if len(users_data) > 200:
                await AnswerCallbackQuery(callback_query_id=call.id, text=f"Слишком много пользователей в потоке для просмотра ({len(users_data)}).", show_alert=True)
                return
            await editShowClassInfo({'name': class_data[1], 'start_date': class_data[2],
                                        'finish_date': class_data[3], 'class_id': admin_data['current_class_editing']}, 
                                        'show_users', call.message.message_id, call.message.chat.id)
            
                    

        # попытка удаления потока
        elif call.data == 'current_class_try_delete':
            admin_data = await state.get_data()
            class_data = await db.get_class(admin_data['current_class_editing'])
            await editShowClassInfo({'name': class_data[1], 'start_date': class_data[2], 'finish_date': class_data[3]}, 
                                    'try_to_delete', call.message.message_id, call.message.chat.id)

        # удаление потока
        elif call.data == 'confirm_deleting class':
            admin_data = await state.get_data()
            class_id = admin_data['current_class_editing']
            users_data = await db.get_class_users(class_id)
            if not users_data:
                await db.delete_class(class_id)
                await editShowClassInfo({}, 'after_deleting', call.message.message_id, call.message.chat.id)
                
                tasks = asyncio.all_tasks()
                
                try:
                    current_task = next(filter(lambda t: t.get_name() == f"{class_id} class_notif", tasks))
                    current_task.cancel()
                    if current_task in notif_tasks:
                        notif_tasks.discard(current_task)
                except:
                    pass
                notif_tasks.add(asyncio.create_task(coro=notifications.class_notification_dispatcher(class_id), 
                                    name=f"{class_id} class_notif"))
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Невозможно удалить поток, так как в нем присутствуют пользователи.",
                                        show_alert=True)


        # изменения нового потока
        elif 'new_class_set_' in call.data:
            changing = call.data.split('_')[3]
            if changing == 'name':
                await state.set_state(ClassPanel.edit_new_class_name)
            elif changing == 'startdate':
                await state.set_state(ClassPanel.edit_new_class_startdate)
            elif changing == 'finishdate':
                await state.set_state(ClassPanel.edit_new_class_finishdate)
            admin_data = await state.get_data()
            await editShowClassInfo(admin_data, f'editing_new_{changing}', call.message.message_id, call.message.chat.id)

        # показать старые потоки
        elif call.data == 'show old class':
            await editShowClassInfo({}, 'show_old', call.message.message_id, call.message.chat.id)

        # назад в основное меню
        elif call.data == 'return_to_menu class':
            await state.update_data(new_class_name=None, new_class_startdate=None, new_class_finishdate=None)
            await editShowClassInfo({}, 'casual', call.message.message_id, call.message.chat.id)

        # закрыть основное меню
        elif call.data == 'close menu class':
            #await editShowClassInfo({}, 'finish', call.message.message_id, call.message.chat.id)
            await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await state.update_data(class_menu_msg=None)

        # подтверждение или отмена закрытия текущего потока
        elif '_move_to_old class' in call.data:
            admin_data = await state.get_data()
            if 'confirm' in call.data:
                class_id = admin_data['current_class_editing']
                await db.edit_class({'finish_date': admin_data['confirming_finishdate'], 'is_present': 0}, class_id)
                await editShowClassInfo({}, 'after_moving_to_old', call.message.message_id, call.message.chat.id)
                await state.update_data(current_class_editing=None)
                tasks = asyncio.all_tasks()
                
                try:
                    current_task = next(filter(lambda t: t.get_name() == f"{class_id} class_notif", tasks))
                    current_task.cancel()
                    if current_task in notif_tasks:
                        notif_tasks.discard(current_task)
                except:
                    pass
                users_data = await db.get_class_current_users(class_id)
                id_list = []
                for user_data in users_data:
                    id_list.append(user_data[0])
                await db.restrict_users(id_list)
                for user_id in id_list:
                    try:
                        await SendMessage(chat_id=user_id, text="Доступ к боту был закрыт в связи с окончанием курса.")
                    except:
                        pass
                    await sleep(1)
            else:
                await state.set_state(ClassPanel.edit_current_class_finishdate)
                class_id = admin_data['current_class_editing']
                await editShowClassInfo(await getInfoToPaste(class_id), 'editing_current_finishdate', 
                                        call.message.message_id, call.message.chat.id)
            await state.update_data(confirming_finishdate=None)

        # создание нового потока
        elif call.data == 'confirm_new_class_create':
            admin_data = await state.get_data()
            if admin_data['new_class_name'] and admin_data['new_class_startdate'] and admin_data['new_class_finishdate']:
                class_id = await db.create_class([admin_data['new_class_name'], admin_data['new_class_startdate'], admin_data['new_class_finishdate']])
                await editShowClassInfo({}, 'after_new_create', call.message.message_id, call.message.chat.id)
                
                notif_tasks.add(asyncio.create_task(coro=notifications.class_notification_dispatcher(class_id), 
                                name=f"{class_id} class_notif"))
                current_sd = await redis.get(name='startdate')
                if current_sd:
                    current_sd = datetime.fromisoformat(str(current_sd.decode()))
                    if datetime.fromisoformat(admin_data['new_class_startdate']) > current_sd:
                        await redis.set(name='startdate', value=str(admin_data['new_class_startdate']))
                else:
                    await redis.set(name='startdate', value=str(admin_data['new_class_startdate']))
                await state.update_data(new_class_name=None, new_class_startdate=None, new_class_finishdate=None)
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text="Заполнены не все поля.", show_alert=True)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)
        



async def showMeetingInfo(data, admin_id, msgid, mode):
    text = "Меню управления лекциями.\n\n"

    if mode == 'casual' or mode == 'after_deleting' or mode == 'after_creating' or mode == 'show_old':
        keyboard = keyboards.admin_meetings_menu_begin()
        if mode == 'after_deleting':
            text += "<b>Лекция успешно удалена.</b>"
        elif mode == 'after_creating':
            text += "<b>Лекция успешно создана.</b>"
        
        """elif mode == 'show_old':
            meetings_data = await db.get_old_meetings() # старая функция
            if meetings_data:
                text += "<b>Старые лекции: </b>"
                i = 0
                for meeting_data in meetings_data:
                    i += 1
                    class_info
                    text += f"{i}. {useless.dateToDDMMYYYY(meeting_data[2])} "
        """
        try:
            await EditMessageText(text=text, chat_id=admin_id, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
        except BaseException as e:
            print(type(e), ': ', e)
        return

    datechange = '<b>Введите дату лекции в формате ДД-ММ-ГГГГ ЧЧ:ММ.</b>'
    linkchange = '<b>Введите ссылку лекции.</b>'
    
    wrongdate = '<b>Дата введена неверно или уже прошла.</b>'
    wronglink = '<b>Неверно введена ссылка.</b>'

    if data['meeting_id'] == 'new':
        date = 'Не выбрана'
        link = 'Не выбрана'
        class_info = 'Не выбран'
        if data['date']:
            date = useless.dateToStr(datetime.fromisoformat(data['date']))
        if data['link']:
            link = data['link']
        if data['class_id']:
            class_data = await db.get_class(data['class_id'])
            class_info = f"{class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})"
    
    
    if mode =='create_new' or mode == 'new_date' or mode == 'new_link' or mode == 'new_potok' or 'wrong_new_' in mode:
        text += "<b>Создание новой лекции.</b>\n"
        text += f"Дата лекции: {date}\n"
        text += f"Ссылка на лекцию: {link}\n"
        text += f"Поток: {class_info}\n\n"
        keyboard = keyboards.admin_meetings_create_new()

        if mode == 'new_date':
            text += datechange
            keyboard = keyboards.admin_meetings_cancel(True)
        elif mode == 'new_link':
            text += linkchange
            keyboard = keyboards.admin_meetings_cancel(True)
        elif mode == 'new_potok':
            classes_data = await db.get_present_classes()
            text += "<b>Выберите поток, к которому будет отнесена лекция:</b>\n"
            i = 0
            for class_data in classes_data:
                i += 1
                text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
            keyboard = keyboards.admin_meetings_choose_class(classes_data, True)
        elif 'wrong_new_' in mode:
            changing = mode.split('_')[2]
            if changing == 'date':
                text += datechange + "\n" + wrongdate
            elif changing == 'link':
                text += linkchange + "\n" + wronglink
            keyboard = keyboards.admin_meetings_cancel(True)
    
    elif mode == 'edit_current':
        text += "<b>Редактирование существующих лекций.</b>\n"
        text += "Выберите поток, лекцию которго необходимо отредактировать.\n"
        classes_data = await db.get_present_classes()
        i = 0
        for class_data in classes_data:
            i += 1
            text += f"{i}. {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])})\n"
        keyboard = keyboards.admin_meetings_choose_class(classes_data, False)

    elif mode == 'editing_current':
        class_data = await db.get_class(data['class_id'])
        text += f"Выбран поток {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n\n"
        meetings_data = list(await db.get_class_meetings(data['class_id']))
        meetings_data = sorted(meetings_data, key=lambda data: datetime.fromisoformat(data[2]))
        if meetings_data:
            text += "Выберите лекцию: \n"
            i = 0
            for meeting_data in meetings_data:
                i += 1
                text += f"{i}. {useless.dateToStr(datetime.fromisoformat(meeting_data[2]))}\n"
        else:
            text += "<b>Лекций для этого потока не найдено. Сначала создайте их.</b>"
        keyboard = keyboards.admin_meetings_choose_conf(meetings_data)

    elif mode == 'conf_to_edit_chosen' or 'edit_current_' in mode or 'edited_current_' in mode\
                or 'wrong_current_' in mode or mode == 'try_cancel':
        class_data = await db.get_class(data['class_id'])
        text += f"Выбран поток {class_data[1]} ({useless.dateToDDMMYYYY(class_data[2])} - {useless.dateToDDMMYYYY(class_data[3])}).\n\n"
        text += f"Информация о лекции: \n"
        meeting_data = await db.get_meeting(data['meeting_id'])
        text += f"Дата: {useless.dateToStr(datetime.fromisoformat(meeting_data[2]))}\n"
        text += f"Ссылка: {meeting_data[3]}\n\n"
        keyboard = keyboards.admin_meetings_edit_current()

        if 'edit_current_' in mode:
            changing = mode.split('_')[2]
            if changing == 'date':
                text += datechange
            elif changing == 'link':
                text += linkchange
            keyboard = keyboards.admin_meetings_cancel(False)

        if 'edited_current_' in mode:
            changing = mode.split('_')[2]
            if changing == 'date':
                text += "<b>Дата успешно изменена.</b>"
            elif changing == 'link':
                text += "<b>Ссылка успешно изменена.</b>"

        if 'wrong_current_' in mode:
            changing = mode.split('_')[2]
            if not 'potok' in mode:
                if changing == 'date':
                    text += datechange + "\n" + wrongdate
                elif changing == 'link':
                    text += linkchange + "\n" + wronglink
            else:
                text += datechange + "\n" + "<b>Дата лекции не может быть вне дат потока.</b>"
            keyboard = keyboards.admin_meetings_cancel(False)

        if mode == 'try_cancel':
            text += "<b>Вы действительно хотите отменить лекцию?</b>"
            keyboard = keyboards.admin_meetings_confirm_cancelling()

    try:
        await EditMessageText(text=text, chat_id=admin_id, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)

@router.callback_query(F.data.contains('meeting'))
async def call_next_meeting(call, state: FSMContext):
    try:
        global notif_tasks
        #meetings_menu_msg=msg.message_id, new_meeting_date=None, new_meeting_link=None, current_meeting_class=None, current_meeting_id=None
        admin_data = await state.get_data()
        data = dict(zip(['msg_id', 'date', 'link', 'class_id', 'meeting_id'], [admin_data['meetings_menu_msg'], admin_data['new_meeting_date'], 
                        admin_data['new_meeting_link'], admin_data['current_meeting_class'], admin_data['current_meeting_id']]))

        # меню создания новой лекции или нажатие кнопки 'отмена' в редактировании чего-либо новой лекции
        if call.data == 'meeting_create' or call.data == 'meeting_return_to_new':
            if call.data == 'meeting_create':
                await state.update_data(current_meeting_id='new')
                data['meeting_id'] = 'new'
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'create_new')
        # главное меню
        elif call.data == 'meeting_return_to_main':
            await state.update_data(new_meeting_date=None, new_meeting_link=None, current_meeting_class=None, current_meeting_id=None)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'casual')
        
        # меню редактирования существующей лекции либо нажатие на кнопку назад из выбора лекций для потока
        elif call.data == 'meeting_edit_current' or call.data == 'return_to_meeting_choose_potok':
            if call.data == 'return_to_meeting_choose_potok':
                await state.update_data(current_meeting_class=None, current_meeting_id=None)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'edit_current')
        
        # нажатие на кнопку выбора потока для текущей лекции либо нажатие на кнопку назад из выбора лекций потока
        elif 'current_meeting_potok ' in call.data or call.data == 'return_to_meeting_choose':
            if 'current_meeting_potok ' in call.data:
                class_id = int(call.data.split()[1])
                data['class_id'] = class_id
                await state.update_data(current_meeting_class=class_id)
            if call.data == 'return_to_meeting_choose':
                await state.update_data(current_meeting_id=None)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'editing_current')

        # нажатие на кнопку выбора лекции для редактирования или нажатие на 'отмена' при редактировании чего-либо
        elif 'choose_meeting_to_edit ' in call.data or call.data == 'meeting_return_to_current':
            if 'choose_meeting_to_edit' in call.data:
                meeting_id = int(call.data.split()[1])
                await state.update_data(current_meeting_id=meeting_id)
                data['meeting_id'] = meeting_id
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'conf_to_edit_chosen')    

        # нажатие на кнопку 'изменить дату' в существующей лекции
        elif call.data == 'current_meeting_date':
            await state.set_state(AdminPanel.choose_next_meeting_date)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'edit_current_date')

        # нажатие на кнопку 'изменить ссылку' в существующей лекции
        elif call.data == 'current_meeting_link':
            await state.set_state(AdminPanel.choose_next_meeting_link)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'edit_current_link')

        # нажатие на кнопку 'отменить лекцию' в существующей лекции
        elif call.data == 'current_meeting_cancel':
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'try_cancel')

        # нажатие на кнопку 'подтвердить' при подтверждении удаления лекции
        elif call.data == 'confirm_cancelling_meeting':
            await db.delete_meeting(admin_data['current_meeting_id'])
            tasks = asyncio.all_tasks()
            
            meeting_id = data['meeting_id']
            try:
                current_task = next(filter(lambda t: t.get_name() == f"{meeting_id} meeting_notif", tasks))
                current_task.cancel()
                if current_task in notif_tasks:
                    notif_tasks.discard(current_task)
            except:
                pass
            await state.update_data(current_meeting_id=None, current_meeting_class=None)
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'after_deleting')
        
        # нажатие на кнопки 'выбрать дату, ссылку, поток' новой лекции 
        elif call.data == 'new_meeting_date' or call.data == 'new_meeting_link' or call.data == 'new_meeting_potok':
            changing = call.data.split('_')[2]
            if changing == 'date':
                await state.set_state(AdminPanel.choose_next_meeting_date)
                await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'new_date')
            elif changing == 'link':
                await state.set_state(AdminPanel.choose_next_meeting_link)
                await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'new_link')
            elif changing == 'potok':
                await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'new_potok')

        elif 'new_meeting_potok ' in call.data:
            class_id = int(call.data.split()[1])
            await state.update_data(current_meeting_class=class_id)
            data['class_id'] = class_id
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'create_new')

        # нажатие на кнопку создать лекцию
        elif call.data == 'new_meeting_final':
            class_id = admin_data['current_meeting_class']
            date = admin_data['new_meeting_date']
            link = admin_data['new_meeting_link']
            if class_id and date and link:
                class_data = await db.get_class(class_id)
                startdate = datetime.fromisoformat(class_data[2])
                finishdate = datetime.fromisoformat(class_data[3])
                meeting_date = datetime.fromisoformat(date)
                if meeting_date > startdate and meeting_date < finishdate:

                    meeting_id = await db.create_meeting([class_id, date, link])
                    
                    notif_tasks.add(asyncio.create_task(coro=notifications.meetings_notification_dispatcher(meeting_id, class_id), 
                                    name=f"{meeting_id} meeting_notif"))
                    await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'after_creating')
                    await state.update_data(new_meeting_date=None, new_meeting_link=None, current_meeting_class=None, current_meeting_id=None)
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Дата лекции не может быть вне дат потока.", show_alert=True)
            else:
                await AnswerCallbackQuery(callback_query_id=call.id, text='Заполнены не все поля.', show_alert=True)

        # нажатие на кнопку 'показать старые лекции'
        elif call.data == 'meeeting_show_old':
            await showMeetingInfo(data, call.message.chat.id, call.message.message_id, 'show_old')

        # нажатие на кнопку 'закрыть меню'
        elif call.data == 'meeting_close_menu':
            await state.update_data(meetings_menu_msg=None)
            await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)



async def showAdminInfo(data, admin_id, user_id, msgid, mode):
    text = 'Меню управления пользователями.'

    if 'choose_name' in mode:
        if mode == 'choose_name_2':
            text += f"\n\nНайдены следующие пользователи:\n\n"
            i = 1
            for row in data:
                text += f"{i}. {row[1]}\n"
                i += 1
            text += "\n<b>Выберите пользователя:</b>"
            keyboard = keyboards.admin_user_choose_name(data)
            await EditMessageText(chat_id=admin_id, text=text, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
            return

        text += f"\n\n<b>Введите часть ФИО пользователя.\n"
        keyboard = keyboards.admin_choose_id_cancel()
        if mode == 'choose_name_too_many':
            text += "Найдено слишком много пользователей, попробуйте ввести более точный запрос."
        elif mode == 'choose_name_nothing':
            text += "Не найдено ни одного пользователя."
        text += "</b>"
        try:
            await EditMessageText(chat_id=admin_id, text=text, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
        except:
            pass
        return

    if data:
        if not data[4]:
            data[4] = "Не выбран"
        if data[6] == 0:
            class_info = 'Не выбран'
        elif not data[6]:
            class_info = 'Не выбран'
        else:
            class_info = await db.get_class(data[6])
            class_info = f"{class_info[1]} ({useless.dateToDDMMYYYY(class_info[2])} - {useless.dateToDDMMYYYY(class_info[3])})"
        match data[8]:
            case '0':
                free_status = 'Не пользовался'
            case 'expired':
                free_status = 'Истёк'
            case _:
                free_status = 'Пользуется сейчас'    
        data[4] = useless.tarifName(data[4])

    
    text += f"\n\nПользователь с ID {user_id}\n\n"
    access = "Открыт" if data[7] else "Закрыт"
    user_info_text = (f"ФИО: {data[1]}.\nНомер телефона: {data[2]}.\n"
                f"Email: {data[3]}.\nТариф: {data[4]}.\n"
                f"Количество оплаченных месяцев: {data[5]}.\nПоток: {class_info}.\n"
                f"Доступ: {access}.\nСтатус пробного периода: {free_status}.\n\n")

    text += user_info_text
    
    if mode == 'show_info':
        text += f"<b>Просмотр информации о пользователе. Выберите дальнейшее действие.</b>"
        keyboard = keyboards.admin_menu_keyboard(data[7])
    elif mode == 'change_tarif':
        text += f"<b>Изменение тарифа. Выберите тариф.</b>"
        keyboard = keyboards.admin_choose('tarif')
    elif mode == 'change_payment':
        text += f"<b>Изменение количества оплаченных месяцев.</b>"
        keyboard = keyboards.admin_months_choose_panel()
    elif mode == 'class_change':
        text += f"<b>Выберите поток, к которому нужно добавить пользователя.</b>\n"
        classes_info = await db.get_present_classes()
        i = 0
        for class_info in classes_info:
            i += 1
            text += f"{i}. {class_info[1]} ({useless.dateToDDMMYYYY(class_info[2])} - {useless.dateToDDMMYYYY(class_info[3])})\n"
        keyboard = keyboards.user_menu_choose_class(classes_info, data[6])
    elif mode == 'restricting_access':
        text += f"<b>Вы действительно хотите ограничить пользователю доступ к тарифу?</b>"
        keyboard = keyboards.confirm()
    elif mode == 'granting_access':
        text += f"<b>Вы действительно хотите предоставить пользователю доступ к тарифу?</b>"
        keyboard = keyboards.confirm()
    elif mode == 'after_tar_change':
        text += f"<b>Успешно установлен тариф «{data[4]}» для пользователя {user_id}.</b>"
    elif 'after_payment_change' in mode:
        text += f"<b>Успешно установлено {data[5]} оплаченных месяцев для пользователя {user_id}.</b>"
        if 'free' in mode:
            text += "\n<b>Пользователь переведён с бесплатного периода на платный доступ.</b>"
    elif mode == 'after_restricting':
        text += f"<b>Пользователю успешно ограничен доступ к тарифу {data[4]}.</b>"
    elif mode == 'after_granting':
        text += f"<b>Пользователю успешно предоставлен доступ к тарифу {data[4]}.</b>"
    elif mode == 'after_class_change':
        text += f"<b>Пользователь {user_id} успешно добавлен к потоку {class_info}.</b>"
    elif mode == 'after_class_delete':
        text += f"<b>У пользователя {user_id} поток успешно очищен.</b>"
    if 'after' in mode:
        keyboard = keyboards.admin_menu_keyboard(data[7])

    try:
        await EditMessageText(chat_id=admin_id, text=text, message_id=msgid, parse_mode='HTML', reply_markup=keyboard)
    except BaseException as e:
        print(type(e), ': ', e)

@router.callback_query()
async def call_process(call, state: FSMContext):
    try:
        global notif_tasks
        if call.data == 'show_info_on_user':
            admin_data = await state.get_data()
            if 'current_id' in admin_data:
                user_id = admin_data['current_id']
            await showAdminInfo(0, call.message.chat.id, 0, admin_data['user_menu_msg'], 'choose_name')
            await state.set_state(AdminPanel.choosing_name)
        elif call.data == 'choose_id_change_cancel':
            admin_data = await state.get_data()
            await EditMessageText(text='Меню управления пользователями.', chat_id=call.message.chat.id, 
                            message_id=admin_data['user_menu_msg'], reply_markup=keyboards.admin_user_menu_begin())
            await state.set_state(None)

        else:
            if 'add_1_months_to_' in call.data:
                user_id = int(call.data.split('_')[4])
                user_data = await db.get_user(user_id)
                if user_data[7] == 1 and user_data[5] != config.maximum_months:
                    months = user_data[5]
                    months += 1
                    await db.admin_menu_user_update(user_id, {'paid_months': months})
                    await EditMessageText(text=f"Успешно добавлен 1 месяц пользователю {user_data[1]} c ID {user_id}.",
                                            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Произошла ошибка. У пользователя нет доступа"
                                            " или у него уже и так оплачен весь курс.", show_alert=True)
                    await EditMessageReplyMarkup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                return
            elif call.data == 'remove_keyboard':
                await EditMessageReplyMarkup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                return
            elif call.data == 'delete_message':
                await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
                return
            elif call.data == 'finish change':
                await state.update_data(user_menu_msg=None)
                await DeleteMessage(chat_id=call.message.chat.id, message_id=call.message.message_id)
                return

            admin_data = await state.get_data()
            user_id = admin_data['current_id']
            user_data = await db.get_user(user_id)
            if call.data == 'tar_change':
                await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'change_tarif')
            elif call.data == 'payment_method_change':
                await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'change_payment')
            elif call.data == 'claass_change':
                #if user_data[7] == 1:
                await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'class_change')
                #else:
                #    await AnswerCallbackQuery(callback_query_id=call.id, 
                #                            text="Невозможно изменить поток, так как у пользователя нет доступа", show_alert=True)
            elif call.data == 'remove_access change':
                await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'restricting_access')
            elif call.data == 'grant_access change':
                if user_data[4] != 'Не выбран' and user_data[5] != 'Не выбран' and user_data[6] != 'Не выбрана':
                    await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'granting_access')
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Заполнены не все поля.", show_alert=True)
            elif call.data == 'cancel change' or call.data == 'back change':
                await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'show_info')
                await state.set_state(None)
                
            

            #изменения пользователей

            elif 'set' in call.data and 'tarif' in call.data:
                tarif = call.data.split()[1]
                if tarif != user_data[4]:
                    await db.admin_menu_user_update(user_id, {'tarif': tarif})
                    user_data[4] = tarif
                    await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_tar_change')
                    if not user_data[8] == 'using' and user_data[7] == 1:
                        try:
                            await SendMessage(chat_id=user_id, text=f"Ваш тариф изменён на «{useless.tarifName(tarif)}» администрацией.")
                            if tarif == '1':
                                await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_1.png"), 
                                caption="Описание тарифа «Самостоятельный»", reply_markup=keyboards.reply(False))
                            elif tarif == '2':
                                await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_2.png"), 
                                caption="Описание тарифа «Хочу большего»", reply_markup=keyboards.reply(True))
                        except:
                            pass
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Выбран тот же тариф.")
            elif 'months' in call.data:
                months = call.data.split()[1]
                if months == 'plus_one':
                    if user_data[5] == config.maximum_months:
                        await AnswerCallbackQuery(callback_query_id=call.id, text="Количество месяцев не может превышать максимальное значение!",
                                                    show_alert=True)
                        return
                    months = user_data[5] + 1
                months = int(months)
                if months != user_data[5]:
                    if not user_data[8] == 'using':
                        await db.admin_menu_user_update(user_id, {'paid_months': months})
                        user_data[5] = months
                        await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_payment_change')
                    else:
                        if not user_data[4] == '0':
                            await db.admin_menu_user_update(user_id, {'paid_months': months, 'free_period_status': 'expired'})
                            try:
                                await SendMessage(chat_id=user_id, text="Вы переведены с пробного периода на платный. Ваш "
                                                                    f"тариф - «{useless.tarifName(user_data[4])}».")
                                if user_data[4] == '1':
                                    await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_1.png"), 
                                    caption="Описание тарифа «Самостоятельный»", reply_markup=keyboards.reply(False))
                                elif user_data[4] == '2':
                                    await SendPhoto(chat_id=user_id, photo=FSInputFile("files/img/tarifs_2.png"), 
                                    caption="Описание тарифа «Хочу большего»", reply_markup=keyboards.reply(True))
                            except:
                                pass
                            user_data[5] = months
                            await showAdminInfo(user_data, call.message.chat.id, user_id, call.message.message_id, 'after_payment_change_free')
                        else:
                            await AnswerCallbackQuery(callback_query_id=call.id, text="Чтобы закончить бесплатный период у пользователя, "
                                                        "необходимо сначала выбрать ему тариф.", show_alert=True)
                else:
                    await AnswerCallbackQuery(callback_query_id=call.id, text="Количество месяцев совпадает с прошлым.")
                
            elif 'set_claass' in call.data:
                class_id = call.data.split()[1]
                if class_id == 'delete':
                    if user_data[7] == 0:
                        if user_data[6] and user_data[6] != 0:
                            await db.admin_menu_user_update(user_id, {'class_id': 0})
                            user_data[6] = 0
                            await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_class_delete')
                        else:
                            await AnswerCallbackQuery(callback_query_id=call.id, text="У пользователя и так не выбран поток.")
                    else:
                        await AnswerCallbackQuery(callback_query_id=call.id, text="Нельзя очистить поток, когда доступ открыт.", show_alert=True)
                else:
                    class_id = int(class_id)
                    if class_id != user_data[6]:
                        await db.admin_menu_user_update(user_id, {'class_id': class_id})
                        user_data[6] = class_id
                        await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_class_change')
                    else:
                        await AnswerCallbackQuery(callback_query_id=call.id, text="Пользователь уже находится в выбранном потоке.")
                



            elif call.data == 'confirm_restrict_grant':

                access = user_data[7]
                
                if access:
                    if user_data[4] == '3' and user_data[8] != 'expired':
                        await db.admin_menu_user_update(user_id, {'tarif': 'Не выбран', 'access': 0, 'free_expiration_date': 'expired'})
                        user_data[7] = 0
                        user_data[4] = 'Не выбран'
                        user_data[8] = 'expired'
                        await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_restricting')
                        try:
                            await SendMessage(chat_id=user_id, text="Ваш доступ к бесплатному периоду ограничен администрацией.", reply_markup=ReplyKeyboardRemove())
                        except:
                            pass
                        return

                    await db.admin_menu_user_update(user_id, {'access': 0})
                    user_data[7] = 0
                    await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_restricting')
                    try:
                        await SendMessage(chat_id=user_id, text="Вам ограничен доступ к тарифу.", reply_markup=ReplyKeyboardRemove())
                    except:
                        pass
                
                else:
                    if user_data[4] != 'Не выбран' and user_data[5] != 0 and user_data[6] != 'Не выбрана':
                        
                        await db.admin_menu_user_update(user_id, {'access': 1})
                        user_data[7] = 1
                        await showAdminInfo(user_data, call.message.chat.id, user_id, admin_data['user_menu_msg'], 'after_granting')
                        if user_data[4] == 'Хочу большего':
                            keyboard = keyboards.reply(True)
                        else:
                            keyboard = keyboards.reply(False)
                        try:
                            await SendMessage(chat_id=user_id, text=f"Доступ к боту открыт.", reply_markup=keyboard)
                        except:
                            pass
                    else:
                        await AnswerCallbackQuery(callback_query_id=call.id, text="Для открытия доступа необходимо заполнить все данные.",
                                        show_alert=True)
    except BaseException as e:
        print(type(e), ': ', e)
        await AnswerCallbackQuery(callback_query_id=call.id, text="Что-то пошло не так.", show_alert=True)
