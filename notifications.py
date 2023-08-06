import config
import bot_db as db
from asyncio import sleep
import useless
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from redis_storage import redis
from datetime import datetime, timedelta
from asyncio import create_task
import keyboards


async def botStartNotifTasks():
    tasks = set()
    classes_data = await db.get_present_classes()
    max_start_date = datetime.fromisoformat('2000-12-31')
    for class_data in classes_data:
        if datetime.fromisoformat(class_data[2]) > max_start_date:
            max_start_date = datetime.fromisoformat(class_data[2])
        class_id = class_data[0]
        tasks.add(create_task(coro=class_notification_dispatcher(class_id), name=f"{class_id} class_notif"))
        meetings_data = await db.get_class_meetings(class_id)
        for meeting_data in meetings_data:
            meeting_id = meeting_data[0]
            tasks.add(create_task(coro=meetings_notification_dispatcher(meeting_id, class_id), name=f"{meeting_id} meeting_notif"))
    if not max_start_date == datetime.fromisoformat('2000-12-31'):
        await redis.set(name='startdate', value=str(max_start_date))
    return tasks


# платежи (потоки):  уведомления в 10 утра, за 4 часа до 00:00, а также конец потока
# лекции: уведомления в 10 утра , за 10 минут и в момент начала
# тесты (после лекций): в 10 утра седьмых суток и за 4 часа до 00:00 (для завершения модуля пройдите тест)

# CLASSES (USERS)

async def class_notification_dispatcher(class_id: int | str): 

    class_data = await db.get_class(class_id)
    startdate = datetime.fromisoformat(class_data[2])
    finishdate = datetime.fromisoformat(class_data[3])
    print('db dates: ', startdate, finishdate)
    
    if finishdate < datetime.now():
        from dispatcher import bot
        class_data = await db.get_class(class_id)
        if class_data[4] == 1:
            users_data = await db.get_class_current_users(class_id)
            users_ids = []
            for user_data in users_data:
                users_ids.append(user_data[0])
            await db.restrict_users(users_ids)
            for user_id in users_ids:
                await bot.send_message(chat_id=user_id, text="Доступ к боту был закрыт в связи с окончанием курса.") 
            for admin_id in config.admins:
                await bot.send_message(chat_id=admin_id, text=f"Поток {class_data[1]} (начавшийся {useless.dateToDDMMYYYY(class_data[2])})"
                                                    " закончился. Всем пользователям закрыт доступ.")
            await db.class_move_to_old(class_id)
            return
    
    now = datetime.now()
    days_diff = timedelta(seconds=(datetime.timestamp(now)-datetime.timestamp(startdate)))

    if days_diff <= timedelta(days=30):
        months = 1
    elif days_diff > timedelta(days=30*config.maximum_months-1):
        months = config.maximum_months
    else:
        for i in range(2, config.maximum_months):
            if days_diff > timedelta(days=30*(i-1)) and days_diff < timedelta(days=30*i):
                months = i
                break
    notif_days = 30*months - 1
    end_days = 30*months

    # бесплатный период
    if months == 1:
        freedate1 = startdate + timedelta(days=6, hours=10) # 6, 10
        freedate2 = startdate + timedelta(days=6, hours=20) # 6, 20
        freedateend = startdate + timedelta(days=7) # 7
        print('freedates: ', freedate1, freedate2, freedateend)
        if now <= freedate1:
            await free_period_notif(freedate1, class_id, freedateend, 'notif')
            now = datetime.now()
        if now <= freedate2:
            await free_period_notif(freedate2, class_id, freedateend, 'notif')
            now = datetime.now()
        await free_period_notif(freedateend, class_id, freedateend, 'end')
    
    # платный период
    if not months == config.maximum_months:
        firstdate = startdate + timedelta(days=notif_days, hours=10)
        seconddate = startdate + timedelta(days=notif_days, hours=20)
        finaldate = startdate + timedelta(days=end_days)
        #firstdate = startdate + timedelta(days=notif_days, hours=17, minutes=6)
        #seconddate = startdate + timedelta(days=notif_days, hours=17, minutes=7)
        #finaldate = startdate + timedelta(days=notif_days, hours=17, minutes=8)
    else:
        firstdate = finishdate - timedelta(hours=14)
        seconddate = finishdate - timedelta(hours=4)
        finaldate = finishdate
        #firstdate = finishdate - timedelta(hours=6, minutes=56)
        #seconddate = finishdate - timedelta(hours=6, minutes=55)
        #finaldate = finishdate - timedelta(hours=6, minutes=54)
    print('payment dates: ', firstdate, seconddate, finaldate)
    if firstdate >= now:
        print('waiting for first notif')
        await class_notif(firstdate, months, class_id)
        now = datetime.now()
    if seconddate >= now:
        print('waiting for second notif')
        await class_notif(seconddate, months, class_id)
        now = datetime.now()
    if finaldate >= now:
        print('waiting for class end')
        await class_end(finaldate, months, class_id, startdate)
    print('done')
    from routers.adminpanel import notif_tasks
    try:
        current_task = next(filter(lambda t: t.get_name() == f"{class_id} class_notif", notif_tasks))
        notif_tasks.discard(current_task)
    except:
        pass

async def free_period_notif(date: datetime, class_id: int | str, freedateend: datetime, mode: str):
    await sleep(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    now = datetime.now()
    users_data = await db.get_class_free_users(class_id)
    from dispatcher import bot
    if mode == 'notif':
        text = (f"Через {useless.secToStr(int(datetime.timestamp(freedateend)) - int(datetime.timestamp(now)))} вам будет ограничен доступ к боту"
                " в связи с окончанием бесплатного периода. Если вы хотите продолжить обучение, напишите нашему менеджеру "
                "@wiseracadem для оплаты курса.")
        for user_data in users_data:
            await bot.send_message(chat_id=user_data[0], text=text, parse_mode='HTML', reply_markup=keyboards.after_free_period())
    elif mode == 'end':
        text = ("Вам был ограничен доступ к боту в связи с окончанием бесплатного периода. "
                "Если вы хотите продолжить обучение, напишите нашему менеджеру "
                "@wiseracadem для оплаты курса.")   
        for user_data in users_data:
            await db.user_free_end(user_data[0])
            try:
                await bot.send_message(chat_id=user_data[0], text=text, reply_markup=keyboards.after_free_period())
            except:
                pass
            await sleep(1)        



async def class_notif(date: datetime, months: int | str, class_id: int | str):
    await sleep(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    print('notif out of sleep')
    from dispatcher import bot
    now = datetime.now()
    end_date = int(datetime.timestamp(datetime.fromisoformat(str(date + timedelta(days=1)).split()[0])))
    time = useless.secToStr(end_date-int(datetime.timestamp(now)))
    users_data = await db.get_class_users_with_months(class_id, months)
    if not months == config.maximum_months:
        text = (f"Завтра в 00:00 (через {time}) "
                    "Вам будет закрыт доступ к боту в связи с неоплатой курса.\n"
                    "Это сообщение приходит тем, кто не оплатил следующий месяц. Если Вы считаете, что это"
                    " сообщение пришло Вам по ошибке, незамедлительно воспользуйтесь кнопкой ниже.")
        keyboard = keyboards.i_paid()
    else:
        text = (f"Завтра в 00:00 (через {time}) Вам будет закрыт доступ к боту в связи с "
                    "окончанием курса.")
        keyboard = None
    for user_data in users_data:
        try:
            await bot.send_message(chat_id=user_data[0], text=text, 
                        parse_mode='HTML', reply_markup=keyboard)
        except:
            pass
        await sleep(1)

async def class_end(date: datetime, months: int, class_id: int | str, startdate: datetime):
    #print(f"sleeping for {timedelta(seconds=int(datetime.timestamp(date))-int(datetime.timestamp(datetime.now())))}")
    await sleep(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    from dispatcher import bot
    users_data = await db.get_class_users_with_months(class_id, months)
    id_list = []
    for user_data in users_data:
        id_list.append(user_data[0])
    await db.restrict_users(id_list)
    if not months == config.maximum_months:
        text = "Доступ к боту был закрыт в связи с неоплатой курса."
    else:
        text = "Доступ к боту был закрыт в связи с окончанием курса."
    for user_id in id_list:
        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=ReplyKeyboardRemove())
        except:
            pass
        await sleep(1)
    
    if not months == config.maximum_months:
        await sleep(1)
        await class_notification_dispatcher(class_id)
    else:
        class_data = await db.get_class(class_id)
        for admin_id in config.admins:
            await bot.send_message(chat_id=admin_id, text=f"Поток {class_data[1]} (начавшийся {useless.dateToDDMMYYYY(class_data[2])})"
                                                    " закончился. Всем пользователям закрыт доступ.")
        await db.class_move_to_old(class_id)


# MEETINGS

async def meetings_notification_dispatcher(meeting_id: int | str, class_id: int | str):
    meeting_data = await db.get_meeting(meeting_id)
    meeting_date = datetime.fromisoformat(meeting_data[2])
    now = datetime.now()
    minutes1 = 60 # 60
    minutes2 = 10 # 10
    firstdate = meeting_date - timedelta(minutes=minutes1)
    
    seconddate = meeting_date - timedelta(minutes=minutes2)
    finaldate = meeting_date
    print(f"meeting_id: {meeting_id} class_id: {class_id} first_date: {firstdate} second_date: {seconddate} final_date: {finaldate}")
    if now <= firstdate: # уведомление запустилось за более чем час
        await meeting_notif(firstdate, class_id, meeting_id, f'before {minutes1}')
        now = datetime.now()
    if now <= seconddate: # уведомление запустилось за более чем 10 минут
        await meeting_notif(seconddate, class_id, meeting_id, f'before {minutes2}')
    
    print(f"all meeting notifications passed, waiting {int(datetime.timestamp(finaldate))-int(datetime.timestamp(datetime.now()))} for meeting")
    await sleep(int(datetime.timestamp(finaldate))-int(datetime.timestamp(datetime.now())))
    print("meeting end out of sleep")
    
    meetings_data = await db.get_old_meetings(class_id)
    prev_meetings_number = len(meetings_data)
    cur_number = prev_meetings_number+1
    
    await db.meeting_move_to_old(meeting_id)
    from dispatcher import bot
    class_data = await db.get_class(class_id)

    keyboard = keyboards.pdf_after_meeting(class_id, cur_number)
    file_data = await db.get_file(cur_number)
    
    text = (f"У потока {class_data[1]} началась лекция.\n"
            f"Подтвердите отправку {cur_number} файла пользователям.")
    if not file_data:
        text += "\n<b>В данный момент файла нет в БД!</b>"
    for admin_id in config.admins:
        await bot.send_message(chat_id=admin_id, text=text, parse_mode='HTML', reply_markup=keyboard)
        
    await meeting_notif(finaldate, class_id, meeting_id, 'now')

    # тесты после лекций
    date1 = meeting_date + timedelta(days=6)
    date1 = str(date1).split()[0]
    date1 = datetime.fromisoformat(str(date1 + ' 10:00:00')) # 10 утра шестых суток
    date2 = date1 + timedelta(hours=10) # 8 вечера шестых суток (за 4 часа до 00:00)
    print(f"test notif dates: {date1}, {date2}")
    date11 = meeting_date + timedelta(seconds=10)
    date22 = meeting_date + timedelta(seconds=20)
    await test_notif(date1, class_id)
    await test_notif(date2, class_id)
    print('test done')
    from routers.adminpanel import notif_tasks
    try:
        current_task = next(filter(lambda t: t.get_name() == f"{meeting_id} meeting_notif", notif_tasks))
        notif_tasks.discard(current_task)
    except:
        pass

async def meeting_notif(date: datetime, class_id: int | str, meeting_id: str | int, mode: str):
    #print(f"meeting class_id: {class_id} sleeping for {timedelta(seconds=int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))}")
    #print(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    await sleep(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    from dispatcher import bot
    users_data = await db.get_class_current_users(class_id)
    meeting_data = await db.get_meeting(meeting_id)
    linktext = f"Ссылка на лекцию: {meeting_data[3]}."
    if 'before' in mode:
        minutes = mode.split()[1]
        for user_data in users_data:
            try:
                await bot.send_message(chat_id=user_data[0], text="Напоминаем, что следующая лекция начнётся через "
                                                                f"{minutes} минут.\n{linktext}")
            except:
                pass
            await sleep(1)
    elif mode == 'now':
        meetings_data = await db.get_class_meetings(class_id)
        min_data = datetime.fromisoformat('2055-01-01')
        changed = False
        for meeting_data in meetings_data:
            if datetime.fromisoformat(meeting_data[2]) < min_data:
                min_data = datetime.fromisoformat(meeting_data[2])
                changed = True
        
        if not changed:
            text = "Администратор пока ещё не назначил дату следующей лекции."
            class_data = await db.get_class(class_id)
            for admin_id in config.admins:
                await bot.send_message(chat_id=admin_id, text=f"У потока {class_data[1]} не назначена дата следующей лекции.")
        else:
            text = f"Следующая лекция назначена на {useless.dateToStr(min_data)}."
        
        for user_data in users_data:
            try:
                await bot.send_message(chat_id=user_data[0], text=f"Лекция началась.\n{linktext}\n{text}")
            except:
                pass
            await sleep(1)
        

async def test_notif(date: datetime, class_id: int | str):
    await sleep(int(datetime.timestamp(date)) - int(datetime.timestamp(datetime.now())))
    from dispatcher import bot
    users_data = await db.get_class_current_users(class_id)
    for user_data in users_data:
        try:
            await bot.send_message(chat_id=user_data[0], text="Напоминаем, что для завершения модуля необходимо пройти тест на платформе progressme.ru.")
        except:
            pass
        await sleep(1)


async def botRestart():
    from dispatcher import bot
    now = datetime.now()
    new_date = now + timedelta(days=1)
    new_date = str(new_date).split()
    new_date = datetime.fromisoformat(str(new_date[0]) + ' 04:59:00')
    await sleep(int(datetime.timestamp(new_date)) - int(datetime.timestamp(now)))
    for admin_id in config.admins:
        await bot.send_message(chat_id=admin_id, text="Через минуту бот перезагрузится.", disable_notification=True)
