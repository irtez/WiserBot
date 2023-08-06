import sqlite3 as sql



async def db_start():
    global db, cursor
    db = sql.connect('sqlite_db.db')
    cursor = db.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(255), "
                    "phone VARCHAR(20), email VARCHAR(255), tarif VARCHAR(20), paid_months INTEGER, "
                    "class_id INTEGER, access INTEGER, free_period_status VARCHAR(10))")
    cursor.execute("CREATE TABLE IF NOT EXISTS meetings(meeting_id INTEGER NOT NULL PRIMARY KEY, "
                    "class_id INTEGER, meeting_date DATE, link VARCHAR(255), is_present INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS classes (class_id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(255), start_date DATE, finish_date DATE, is_present INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS files (file_id INTEGER NOT NULL PRIMARY KEY, link VARCHAR(100))")
    db.commit()


#USERS
async def create_user(user_id):
    user = cursor.execute(f"SELECT * FROM users WHERE user_id = {user_id}").fetchone()
    if not user:
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (user_id, '', '', 
                        '', '', '', 0, 0, 0))
        db.commit()

async def update_user(data, user_id, mode):
    if mode == 'registration_complete':
        cursor.execute("UPDATE users SET name = :name, phone = :phone, email = :email, tarif = :tarif, "
                    "paid_months = :paid_months, class_id = :class WHERE user_id = :user_id", 
                    {'name': data['name'], 'phone': data['phone'], 'email': data['email'], 'user_id': user_id,
                    'tarif': data['tarif'], 'paid_months': data['paid_months'], 'class': data['class_id']})
    elif mode == 'user_status_update':
        cursor.execute("UPDATE users SET tarif = :tarif, paid_months = :pay, class_id = :class, access = :access WHERE user_id = :user_id", 
                    {'tarif': data['tarif'], 'pay': data['paid_months'], 'class': data['class_id'], 'access': data['access'], 'user_id': user_id})
    elif mode == 'free_period_begin':
        cursor.execute("UPDATE users SET name = :name, phone = :phone, email = :email, tarif = :tarif, access = :access, free_period_status = :date"
                        " WHERE user_id = :user_id", {'name': data['name'], 'phone': data['phone'], 'email': data['email'], 
                        'tarif': 3, 'access': 1, 'date': data['free_expir_date'], 'user_id': user_id})
    db.commit()

async def admin_menu_user_update(user_id, data: dict):
    text = "UPDATE users SET "
    for column in data:
        text += f"{column} = :{column}, "
    text = text[:-2]
    text += " WHERE user_id = :user_id"
    
    data['user_id'] = user_id
    cursor.execute(text, data)
    db.commit()

async def search_user(name):
    user_data = cursor.execute(f"SELECT user_id, name FROM users WHERE name LIKE '%{name}%'").fetchall()
    return user_data
    
async def get_user(user_id):
    user_data = cursor.execute(f"SELECT * FROM users WHERE user_id = {user_id}").fetchall()
    return list(user_data[0])

async def get_users_with_access(tarif: list):
    spisok = []
    for i in tarif:
        text = f"SELECT user_id, paid_months, class_id FROM users WHERE tarif = '{i}' and access = 1"
        spisok += cursor.execute(text).fetchall()
    return spisok

async def restrict_users(users_ids: list):
    for user_id in users_ids:
        text = "UPDATE users SET access = 0 WHERE user_id = :user_id"
        cursor.execute(text, {'user_id': user_id})
    db.commit()
    
async def user_free_end(user_id: int | str):
    text = "UPDATE users SET access = 0, free_period_status = 'expired' WHERE user_id = :user_id"
    cursor.execute(text, {'user_id': user_id})
    db.commit()



    
# MEETINGS
async def get_meeting(meeting_id):
    data = cursor.execute(f"SELECT * FROM meetings WHERE meeting_id = :meeting_id", {'meeting_id': meeting_id}).fetchall()
    return list(data[0])

async def get_class_meetings(class_id: int | str):
    data = cursor.execute(f"SELECT * FROM meetings WHERE class_id = :class_id AND is_present = 1", {'class_id': class_id}).fetchall()
    return data

async def update_meeting(data: dict, meeting_id: int | str):
    text = "UPDATE meetings SET "
    for key in data.keys():
        text += f"{key} = :{key}, "
    text = text[:-2]
    text += " WHERE meeting_id = :meeting_id"
    data['meeting_id'] = meeting_id
    cursor.execute(text, data)
    db.commit()

async def create_meeting(data: list):
    text = "INSERT INTO meetings (class_id, meeting_date, link, is_present) VALUES (?, ?, ?, ?)"
    data.append(1)
    cursor.execute(text, data)
    db.commit()
    data = cursor.execute("SELECT meeting_id FROM meetings WHERE class_id = :ci AND meeting_date = :md AND link = :link AND is_present = :ip", 
                    {'ci': data[0], 'md': data[1], 'link': data[2], 'ip': data[3]}).fetchall()
    return data[-1][0]


async def delete_meeting(meeting_id: int | str):
    text = "DELETE FROM meetings WHERE meeting_id = :meeting_id"
    cursor.execute(text, {'meeting_id': meeting_id})
    db.commit()

async def get_old_meetings(class_id: int | str):
    text = "SELECT * FROM meetings WHERE class_id = :class_id AND is_present = 0"
    data =  cursor.execute(text, {'class_id': class_id}).fetchall()
    return data

async def meeting_move_to_old(meeting_id: int | str):
    text = "UPDATE meetings SET is_present = 0 WHERE meeting_id = :meeting_id"
    cursor.execute(text, {'meeting_id': meeting_id})
    db.commit()
        



# CLASSES
async def get_present_classes():
    data = cursor.execute("SELECT * FROM classes WHERE is_present = 1").fetchall()
    return data

async def get_old_classes():
    data = cursor.execute("SELECT * FROM classes WHERE is_present = 0").fetchall()
    return data

async def edit_class(data: dict, class_id: int):
    text = "UPDATE classes SET "
    for key in data.keys():
        text += f"{key} = :{key}, "
    text = text[:-2]
    text += " WHERE class_id = :class_id"
    data['class_id'] = class_id
    cursor.execute(text, data)
    db.commit()

async def get_class(class_id: int | str):
    data = cursor.execute("SELECT * FROM classes WHERE class_id = :class_id", {'class_id': class_id}).fetchall()
    return list(data[0])

async def create_class(class_data: list):
    class_data.append(1)
    text = "INSERT INTO classes (name, start_date, finish_date, is_present) VALUES (?, ?, ?, ?)"
    cursor.execute(text, class_data)
    db.commit()
    data = cursor.execute("SELECT class_id FROM classes WHERE name = :name AND start_date = :sd AND finish_date = :fd AND is_present = :ip", 
                    {'name': class_data[0], 'sd': class_data[1], 'fd': class_data[2], 'ip': 1}).fetchall()
    return data[-1][0]

async def delete_class(class_id: int | str):
    text = "DELETE FROM classes WHERE class_id = :class_id"
    cursor.execute(text, {'class_id': class_id})
    db.commit()


async def get_class_users(class_id: int | str):
    text = "SELECT name FROM users WHERE class_id = :class_id"
    data = cursor.execute(text, {'class_id': class_id}).fetchall()
    return data

async def get_class_current_users(class_id: int | str):
    text = "SELECT * FROM users WHERE class_id = :class_id AND access = 1"
    data = cursor.execute(text, {'class_id': class_id}).fetchall()
    return data

async def get_class_users_with_months(class_id: int | str, months: int| str):
    text = "SELECT user_id FROM users WHERE class_id = :class_id AND paid_months <= :months AND access = 1"
    data = cursor.execute(text, {'class_id': class_id, 'months': months}).fetchall()
    return data

async def class_move_to_old(class_id: int | str):
    text = "UPDATE classes SET is_present = 0 WHERE class_id = :class_id"
    cursor.execute(text, {'class_id': class_id})
    db.commit()

async def get_class_free_users(class_id: int | str):
    text = "SELECT * FROM users WHERE class_id = :class_id AND free_period_status = :status AND access = 1"
    data = cursor.execute(text, {'class_id': class_id, 'status': 'using'}).fetchall()
    return data

async def get_class_users_with_tarif(class_id: int | str, tarifs: list):
    data = []
    for tarif in tarifs:
        text = "SELECT user_id FROM users WHERE class_id = :class_id AND access = 1 AND tarif = :tarif"
        tarif_data = cursor.execute(text, {'class_id': class_id, 'tarif': tarif}).fetchall()
        data += tarif_data
    return data

# FILES
async def get_all_files():
    text = "SELECT * FROM files"
    data = cursor.execute(text).fetchall()
    return data

async def get_file(file_id: int | str):
    text = "SELECT * FROM files WHERE file_id = :file_id"
    data = cursor.execute(text, {'file_id': file_id}).fetchall()
    return data

async def delete_file(file_id: int | str):
    text = "DELETE FROM files WHERE file_id = :file_id"
    cursor.execute(text, {'file_id': file_id})
    db.commit()

async def create_file(file_id: int | str, doc_id: int | str):
    text = "INSERT INTO files (file_id, link) VALUES (?, ?)"
    cursor.execute(text, [file_id, doc_id])
    db.commit()

async def edit_file(file_id: int | str, doc_id: int | str):
    text = "UPDATE files SET link = :link WHERE file_id = :file_id"
    cursor.execute(text, {'link': doc_id, 'file_id': file_id})
    db.commit()

# MAIL
async def get_userids_with_params(tarifs: list, classes: list | str, isAll: bool = False):
    if isAll:
        data = cursor.execute("SELECT user_id FROM users").fetchall()
        return data
    result_dict = {}
    text = "SELECT user_id FROM users WHERE "
    i = 0
    for tarif in tarifs:
        if tarif == '3':
            text += "free_period_status = 'using' OR "
        else:
            i += 1
            text += f"tarif = :tarif{i} OR "
            result_dict[f'tarif{i}'] = tarif
    text = text[:-3]
    if not classes == 'ALL':
        text += "AND "
        i = 0
        for class_id in classes:
            i += 1
            text += f"class_id = :class_id{i} OR "
            result_dict[f'class_id{i}'] = class_id
        text = text[:-3]
    text += "AND access = 1"
    data = cursor.execute(text, result_dict).fetchall()
    return data

# EXPORT
async def select_all(db: str):
    text = f"SELECT * from {db}"
    data = cursor.execute(text).fetchall()
    return data