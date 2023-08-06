from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from config import maximum_months

def admin_user_menu_begin():
    markup = InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text='Посмотреть информацию о пользователе', callback_data='show_info_on_user'))
    markup.row(InlineKeyboardButton(text='Закрыть меню', callback_data='finish change'))
    return markup.as_markup()

def otmena(date=False):
    markup = InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text='Отмена', callback_data='cancel change'))
    return markup.as_markup()

def confirm():
    markup = InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text='Подтвердить', callback_data='confirm_restrict_grant'))
    markup.row(InlineKeyboardButton(text='Отмена', callback_data='cancel change'))
    return markup.as_markup()

def admin_choose(mode):
    markup = InlineKeyboardBuilder()
    if mode == 'tarif':
        markup.row(InlineKeyboardButton(text='Тариф «Самостоятельный»', callback_data='set 1 tarif'),
        InlineKeyboardButton(text='Тариф «Хочу большего»', callback_data='set 2 tarif'))
    """elif mode == 'payment':
        markup.row(InlineKeyboardButton(text='Частичная оплата', callback_data='set part payment'), 
        InlineKeyboardButton(text='Полная оплата', callback_data='set full payment'))"""
    markup.row(InlineKeyboardButton(text='Назад', callback_data='back change'))
    return markup.as_markup()

def admin_menu_keyboard(access):
    markup = InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text='Перейти к другому пользователю', callback_data='show_info_on_user'))
    markup.row(InlineKeyboardButton(text='Поменять тариф пользователя', callback_data='tar_change'))
    markup.row(InlineKeyboardButton(text='Поменять кол-во оплаченных месяцев', callback_data='payment_method_change'))
    markup.row(InlineKeyboardButton(text='Поменять поток пользователя', callback_data='claass_change'))
    if access:
        markup.row(InlineKeyboardButton(text='Ограничить доступ пользователю', callback_data='remove_access change'))
    else:
        markup.row(InlineKeyboardButton(text='Предоставить доступ пользователю', callback_data='grant_access change'))
    markup.row(InlineKeyboardButton(text='Закрыть меню', callback_data='finish change'))
    return markup.as_markup()
    


def KBBuilder(chat_id):
    builder2 = InlineKeyboardBuilder()
    builder2.row(InlineKeyboardButton(text='Отклонить запрос', callback_data=f"cancel {chat_id} adm"))
    builder2.row(InlineKeyboardButton(text='Тариф «Самостоятельный»', callback_data=f"tar1 {chat_id} adm"), 
                InlineKeyboardButton(text='Тариф «Хочу большего»', callback_data=f"tar2 {chat_id} adm"))
    builder2.row(InlineKeyboardButton(text='Установить кол-во оплаченных месяцев', callback_data=f"choose_payment {chat_id} adm"))
    builder2.row(InlineKeyboardButton(text='Установить поток', callback_data=f"choose_class {chat_id} adm"))
    builder2.row(InlineKeyboardButton(text='Подтвердить выбор', callback_data=f"confirm {chat_id} adm"))
    return builder2.as_markup()



def user_reg_change(free_period_expired: bool = False):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Поменять ФИО', callback_data = 'fio_change'), 
                InlineKeyboardButton(text='Поменять номер', callback_data = 'phone_change'))
    builder.row(InlineKeyboardButton(text='Поменять e-mail', callback_data = 'email_change'))
    builder.row(InlineKeyboardButton(text='Записаться на курс', callback_data = 'preconfirm'))
    if not free_period_expired:
        builder.row(InlineKeyboardButton(text='Начать пробный период', callback_data = 'try_free'))
    return builder.as_markup()

def user_reg_cancel():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='cancel_user_change'))
    return builder.as_markup()

def user_free_period_confirm():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data='confirm_free_period'))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='cancel_user_change'))
    return builder.as_markup() 

def user_tarif_confirm():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data='confirm_data'))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='cancel_user_change'))
    return builder.as_markup() 

def admin_reject_tarif():
    pass

def admin_choose_id_cancel():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='choose_id_change_cancel'))
    return builder.as_markup()

def reject_access_adm(date):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отправить запрос заново', callback_data="confirm_data_again"))
    if date == '0':
        builder.row(InlineKeyboardButton(text='Попробовать пробный период', callback_data="try_free_from_again"))
    return builder.as_markup()

def cancel_free_from_again():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Да', callback_data="confirm_free_from_again"))
    builder.row(InlineKeyboardButton(text='Назад', callback_data="reject_free_from_again"))
    return builder.as_markup()

def admin_user_choose_name(data):
    builder = InlineKeyboardBuilder()
    i = 1
    for row in data:
        builder.row(InlineKeyboardButton(text=i, callback_data=f"choose_name {row[0]}"))
        i += 1
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='choose_id_change_cancel'))
    return builder.as_markup()

def admin_request_cancel_change(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"abandon_change {user_id} adm"))
    return builder.as_markup()

def admin_months_choose(user_id):
    builder = InlineKeyboardBuilder()
    a = 0
    builder.row(InlineKeyboardButton(text='Добавить 1 месяц', callback_data=f"months {user_id} plus_one adm"))
    if maximum_months % 2 == 1:
        for i in range((maximum_months)//2+1):
            builder.row(InlineKeyboardButton(text=str(a), callback_data=f"months {user_id} {a} adm"),
            InlineKeyboardButton(text=str(a+1), callback_data=f"months {user_id} {a+1} adm"))
            a += 2
    else:
        for i in range((maximum_months)//2):
            builder.row(InlineKeyboardButton(text=str(a), callback_data=f"months {user_id} {a} adm"),
            InlineKeyboardButton(text=str(a+1), callback_data=f"months {user_id} {a+1} adm"))
            a += 2
        builder.row(InlineKeyboardButton(text=str(maximum_months), callback_data=f"months {user_id} {maximum_months} adm"))
    
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"abandon_change {user_id} adm"))
    return builder.as_markup()
    
def admin_months_choose_panel():
    builder = InlineKeyboardBuilder()
    a = 0
    builder.row(InlineKeyboardButton(text='Добавить 1 месяц', callback_data=f"months plus_one"))
    if maximum_months % 2 == 1:
        for i in range((maximum_months)//2+1):
            builder.row(InlineKeyboardButton(text=str(a), callback_data=f"months {a}"),
            InlineKeyboardButton(text=str(a+1), callback_data=f"months {a+1}"))
            a += 2
    else:
        for i in range((maximum_months)//2):
            builder.row(InlineKeyboardButton(text=str(a), callback_data=f"months {a}"),
            InlineKeyboardButton(text=str(a+1), callback_data=f"months {a+1}"))
            a += 2
        builder.row(InlineKeyboardButton(text=str(maximum_months), callback_data=f"months {maximum_months}"))
    
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"cancel change"))
    return builder.as_markup()

def register_start():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Зарегистрироваться', callback_data="register"))
    return builder.as_markup()

def change_info():
    builder = InlineKeyboardBuilder()
    #builder.row(InlineKeyboardButton(text='Поменять ФИО', callback_data=f"new_name"))
    builder.row(InlineKeyboardButton(text='Поменять номер телефона', callback_data=f"new_phone"))
    builder.row(InlineKeyboardButton(text='Поменять e-mail', callback_data=f"new_email"))
    builder.row(InlineKeyboardButton(text='Подтвердить изменения', callback_data=f"new_finish"))
    builder.row(InlineKeyboardButton(text='Закрыть меню и отменить изменения', callback_data=f"new_cancel_all"))
    return builder.as_markup()

def change_info_cancel():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"new_cancel"))
    return builder.as_markup()

def after_free_period():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Написать менеджеру', url='t.me/wiseracadem'))
    return builder.as_markup()

def admin_request_class_choose(classes_data, user_id):
    builder = InlineKeyboardBuilder()
    i = 0
    for class_data in classes_data:
        i += 1
        builder.row(InlineKeyboardButton(text=f"{i}. {class_data[1]}", callback_data=f"class {user_id} {class_data[0]} adm"))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"abandon_change {user_id} adm"))
    return builder.as_markup()


# CLASSES MENU
def admin_class_menu_begin():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Создать новый поток', callback_data="create new class"))
    builder.row(InlineKeyboardButton(text='Редактировать текущие потоки', callback_data="edit present class"))
    #builder.row(InlineKeyboardButton(text='Посмотреть старые потоки', callback_data="show old class"))
    builder.row(InlineKeyboardButton(text='Закрыть меню', callback_data="close menu class"))
    return builder.as_markup()

def admin_class_menu_create():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Выбрать название потока', callback_data="new_class_set_name"))
    builder.row(InlineKeyboardButton(text='Установить дату начала', callback_data="new_class_set_startdate"))
    builder.row(InlineKeyboardButton(text='Установить дату конца', callback_data="new_class_set_finishdate"))
    builder.row(InlineKeyboardButton(text='Создать поток', callback_data="confirm_new_class_create"))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data="return_to_menu class"))
    return builder.as_markup()

def admin_class_choose_present_class(classes_data):
    builder = InlineKeyboardBuilder()
    i = 0
    for class_data in classes_data:
        i += 1
        builder.row(InlineKeyboardButton(text=f"{i}. {class_data[1]}", callback_data=f"edit_present_class {class_data[0]}"))
    builder.row(InlineKeyboardButton(text='Назад', callback_data="return_to_menu class"))
    return builder.as_markup()

def admin_class_edit_present():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Изменить название потока', callback_data="current_class_edit_name"))
    builder.row(InlineKeyboardButton(text='Изменить дату начала', callback_data="current_class_edit_startdate"))
    builder.row(InlineKeyboardButton(text='Изменить дату конца', callback_data="current_class_edit_finishdate"))
    builder.row(InlineKeyboardButton(text='Показать пользователей', callback_data="current_class_show_users"))
    builder.row(InlineKeyboardButton(text='Удалить поток', callback_data="current_class_try_delete"))
    builder.row(InlineKeyboardButton(text='Назад', callback_data="return_to_show_current_classes"))
    return builder.as_markup()

def admin_class_back_to_current():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data="back_to_show_current_class"))
    return builder.as_markup()


def admin_class_back_to_current2():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Назад', callback_data="back_to_show_current_class"))
    return builder.as_markup()

def admin_class_back_to_new():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data="back_to_new_class"))
    return builder.as_markup()

def admin_class_pure_back_to_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Назад', callback_data="return_to_menu class"))
    return builder.as_markup()

def admin_class_confirm_deleting():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data="confirm_deleting class"))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data="back_to_show_current_class"))
    return builder.as_markup()

def confirm_move_to_old():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data="confirm_move_to_old class"))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data="reject_move_to_old class"))
    return builder.as_markup()

# USER MENU
def user_menu_choose_class(classes_data, current_class):
    builder = InlineKeyboardBuilder()
    i = 0
    if current_class and current_class != 0:
        builder.row(InlineKeyboardButton(text='Очистить поток', callback_data=f"set_claass delete"))
    for class_data in classes_data:
        i += 1
        builder.row(InlineKeyboardButton(text=f"{i}. {class_data[1]}", callback_data=f"set_claass {class_data[0]}"))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f"cancel change"))
    return builder.as_markup()


# MEETINGS MENU

def admin_meetings_menu_begin():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Создать новую лекцию', callback_data='meeting_create')) 
    builder.row(InlineKeyboardButton(text='Редактировать существующие', callback_data='meeting_edit_current'))
    #builder.row(InlineKeyboardButton(text='Посмотреть старые лекции', callback_data='meeeting_show_old'))
    builder.row(InlineKeyboardButton(text='Закрыть меню', callback_data='meeting_close_menu'))
    return builder.as_markup()

def admin_meetings_create_new():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Выбрать дату', callback_data='new_meeting_date'))
    builder.row(InlineKeyboardButton(text='Выбрать ссылку', callback_data='new_meeting_link'))
    builder.row(InlineKeyboardButton(text='Выбрать поток', callback_data='new_meeting_potok'))
    builder.row(InlineKeyboardButton(text='Создать лекцию', callback_data='new_meeting_final'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='meeting_return_to_main'))
    return builder.as_markup()

def admin_meetings_edit_current():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Изменить дату', callback_data='current_meeting_date'))
    builder.row(InlineKeyboardButton(text='Изменить ссылку', callback_data='current_meeting_link'))
    builder.row(InlineKeyboardButton(text='Отменить лекцию', callback_data='current_meeting_cancel'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='return_to_meeting_choose'))
    return builder.as_markup()

def admin_meetings_choose_class(classes_data: list | set, isNew: bool):
    builder = InlineKeyboardBuilder()
    i = 0
    text = "new" if isNew else "current"
    text2 = "meeting_return_to_new" if isNew else "meeting_return_to_main"
    for class_data in classes_data:
        i += 1
        builder.row(InlineKeyboardButton(text=f"{i}. {class_data[1]}", callback_data=f'{text}_meeting_potok {class_data[0]}'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data=text2))
    return builder.as_markup()

def admin_meetings_cancel(isNew: bool):
    builder = InlineKeyboardBuilder()
    text = "new" if isNew else "current"
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f'meeting_return_to_{text}'))
    return builder.as_markup()

def admin_meetings_choose_conf(meetings_data: list | set):
    builder = InlineKeyboardBuilder()
    i = 0
    for meeting_data in meetings_data:
        i += 1
        builder.row(InlineKeyboardButton(text=f"{i}", callback_data=f'choose_meeting_to_edit {meeting_data[0]}'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data=f'return_to_meeting_choose_potok'))
    return builder.as_markup()

def admin_meetings_confirm_cancelling():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data='confirm_cancelling_meeting'))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='meeting_return_to_current'))
    return builder.as_markup()

# NOTIFICATIONS
def i_paid():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Я уже оплатил', callback_data='i_paid'))
    builder.row(InlineKeyboardButton(text='Я оплачу до 00:00', callback_data='i_will_pay'))
    return builder.as_markup()

def i_paid_admin(user_id: int | str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Добавить 1 месяц', callback_data=f'add_1_months_to_{user_id}'))
    builder.row(InlineKeyboardButton(text='Убрать клавиатуру', callback_data='remove_keyboard'))
    builder.row(InlineKeyboardButton(text='Удалить это сообщение', callback_data='delete_message'))
    return builder.as_markup()

def pdf_after_meeting(class_id: int | str, num: int | str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отправить', callback_data=f'send_pdf {num} {class_id}'))
    builder.row(InlineKeyboardButton(text='Отправить другой файл', callback_data=f'change_pdf {num} {class_id}'))
    return builder.as_markup()

def change_pdf_meeting(class_id: int | str, num: int | str):
    builder = InlineKeyboardBuilder()
    for i in range(0, 6):
        builder.row(InlineKeyboardButton(text=i*3+1, callback_data=f'conf_pdf {i*3+1} {class_id}'),
                    InlineKeyboardButton(text=i*3+2, callback_data=f'conf_pdf {i*3+2} {class_id}'),
                    InlineKeyboardButton(text=i*3+3, callback_data=f'conf_pdf {i*3+3} {class_id}'))
    builder.row(InlineKeyboardButton(text=19, callback_data=f'conf_pdf 19 {class_id}'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data=f'pdf_back {num} {class_id}'))
    return builder.as_markup()

# FILE MENU
def file_menu_start():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Посмотреть имеющиеся файлы', callback_data=f'file show'))
    builder.row(InlineKeyboardButton(text='Изменить файлы', callback_data=f'file changedelete'))
    builder.row(InlineKeyboardButton(text='Закрыть меню', callback_data=f'file close'))
    return builder.as_markup()

def show_files(files_dict: dict):
    builder = InlineKeyboardBuilder()
    file_list = []
    for file_id in files_dict:
        if files_dict[file_id] == 'есть':
            file_list.append(file_id)
    for file_id in file_list:
        builder.row(InlineKeyboardButton(text=file_id, callback_data=f'show_file {file_id}'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='file back to main'))
    return builder.as_markup()

def change_delete_files():
    builder = InlineKeyboardBuilder()
    for i in range(0, 6):
        builder.row(InlineKeyboardButton(text=i*3+1, callback_data=f'file_choose {i*3+1}'),
                    InlineKeyboardButton(text=i*3+2, callback_data=f'file_choose {i*3+2}'),
                    InlineKeyboardButton(text=i*3+3, callback_data=f'file_choose {i*3+3}'))
    builder.row(InlineKeyboardButton(text=19, callback_data=f'file_choose 19'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='file back to main'))
    return builder.as_markup()

def file_options(file_id: int | str, exists: bool):
    builder = InlineKeyboardBuilder()
    if exists:
        builder.row(InlineKeyboardButton(text='Изменить файл', callback_data=f'change_file {file_id}'))
        builder.row(InlineKeyboardButton(text='Удалить файл', callback_data=f'delete_file_try {file_id}'))
    else:
        builder.row(InlineKeyboardButton(text='Добавить файл', callback_data=f'add_file {file_id}'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='file back to changedel'))
    return builder.as_markup()

def file_deleting(file_id: int | str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Подтвердить', callback_data=f'delete_file {file_id}'))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f'file_back_to_options {file_id}'))
    return builder.as_markup()

def back_out_of_file_options(file_id: int | str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=f'file_back_to_options {file_id}'))
    return builder.as_markup()
    
    
# MAIL
def mailing_start(tarifs: list):
    builder = InlineKeyboardBuilder()
    if not tarifs:
        builder.row(InlineKeyboardButton(text='Всем пользователям', callback_data='mailing_all'))
    if not '1' in tarifs:
        builder.row(InlineKeyboardButton(text='Добавить «Самостоятельный»', callback_data='mailing_add_1'))
    else:
        builder.row(InlineKeyboardButton(text='Убрать «Самостоятельный»', callback_data='mailing_del_1'))
    if not '2' in tarifs:
        builder.row(InlineKeyboardButton(text='Добавить «Хочу большего»', callback_data='mailing_add_2'))
    else:
        builder.row(InlineKeyboardButton(text='Убрать «Хочу большего»', callback_data='mailing_del_2'))
    if not '3' in tarifs:
        builder.row(InlineKeyboardButton(text='Добавить бесплатный период', callback_data='mailing_add_3'))
    else:
        builder.row(InlineKeyboardButton(text='Убрать бесплатный период', callback_data='mailing_del_3'))
    if tarifs:
        builder.row(InlineKeyboardButton(text='→ Далее →', callback_data='mailing_to_potok'))
    else:
        builder.row(InlineKeyboardButton(text='Закрыть меню', callback_data='mailing_close'))
    return builder.as_markup()

def mailing_back_to_main():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='mailing_to_main_all'))
    return builder.as_markup()

def mailing_choose_class(classes_data: list | set, existing_classes: list):
    builder = InlineKeyboardBuilder()
    i = 0
    if classes_data:
        builder.row(InlineKeyboardButton(text='ВСЕ', callback_data='mailing_class_all'))
    for class_data in classes_data:
        i += 1
        if existing_classes:
            if not class_data[0] in existing_classes:
                builder.row(InlineKeyboardButton(text=f'{i}. {class_data[1]} добавить', callback_data=f'mailing_class_add_{class_data[0]}'))
            else:
                builder.row(InlineKeyboardButton(text=f'{i}. {class_data[1]} убрать', callback_data=f'mailing_class_del_{class_data[0]}'))
        else:
            builder.row(InlineKeyboardButton(text=f'{i}. {class_data[1]} добавить', callback_data=f'mailing_class_add_{class_data[0]}'))
    if existing_classes:
        builder.row(InlineKeyboardButton(text='→ Далее →', callback_data='mailing_final_send'))
    builder.row(InlineKeyboardButton(text='Назад', callback_data='mailing_to_main'))
    return builder.as_markup()

def mailing_back_to_potok():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='mailing_to_potok'))
    return builder.as_markup()


def mailing_confirm_send(from_all: bool): 
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отправить', callback_data='mailing_confirm_send'))
    if from_all:
        text = 'mailing_to_main_all'
    else:
        text = 'mailing_to_potok'
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=text)) #настроить удаление инфы о сообщениях
    return builder.as_markup()

def mailing_delete_message():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Убрать это сообщение", callback_data='delete_message'))
    return builder.as_markup()

# HELP
def help_msg():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Связь с менеджером", url='https://t.me/wiseracadem'))
    return builder.as_markup()


def reply(isMore: bool):
    """
    buttons_list = [
        [KeyboardButton(text="Расписание лекций 🗓"), KeyboardButton(text="Информация о курсе 🗂")],
        [KeyboardButton(text="Персональные данные 👤"), KeyboardButton(text="Помощь по боту 🛠")]
    ]
    buttons_list.append([KeyboardButton(text="Связь с преподавателем 👩🏻‍🏫")])
    """
    buttons_list = [
        [KeyboardButton(text="Информация о курсе 🗂")],
        [KeyboardButton(text="Расписание лекций 🗓")],
        [KeyboardButton(text="Связь с преподавателем 👩🏻‍🏫")],
        [KeyboardButton(text="Персональные данные 👤")],
        [KeyboardButton(text="Помощь по боту 🛠")]
        ]
    markup = ReplyKeyboardMarkup(keyboard=buttons_list, resize_keyboard=True)
    return markup

def reply2(isMore: bool):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Расписание лекций 🗓"), KeyboardButton(text="Информация о курсе 🗂"))
    builder.row(KeyboardButton(text="Персональные данные 👤"), KeyboardButton(text="Помощь по боту 🛠"))
    builder.row(KeyboardButton(text="Связь с преподавателем 👩🏻‍🏫"))
    return builder.as_markup()

def teacher():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Связь с преподавателем", url='https://t.me/mssnataliya'))
    return builder.as_markup()

def export():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Пользователи', callback_data='export 1'))
    builder.row(InlineKeyboardButton(text='Потоки', callback_data='export 2'))
    builder.row(InlineKeyboardButton(text='Лекции', callback_data='export 3'))
    builder.row(InlineKeyboardButton(text="Закрыть меню", callback_data='delete_message'))
    return builder.as_markup()