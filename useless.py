import datetime


def monthToStr(month: int):
    month_dict = {1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая',
                6: 'июня', 7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября',
                11: 'ноября', 12: 'декабря'}
    return month_dict[month]

def dateToStr(date: datetime.datetime):
    hour = date.hour
    if len(str(date.hour)) == 1:
        hour = "0" + str(date.hour)
    minute = date.minute
    if len(str(date.minute)) == 1:
        minute = "0" + str(date.minute)
    return f"{hour}:{minute} {date.day} {monthToStr(date.month)} {date.year} года"

def secToStr(seconds: int):
    hours = seconds//3600
    seconds = seconds - hours*3600
    minutes = seconds//60
    seconds = seconds - minutes*60
    text = ''
    if hours:
        last_h = int(str(hours)[-1:])
        hours_dict = {
            last_h == 1: 'час',
            2 <= last_h <= 4: 'часа',
            last_h >= 5 or last_h == 0: 'часов',
            hours > 10 and hours < 20: 'часов'
        }
        
        text += str(hours) + ' ' + str(hours_dict[True])
    if minutes:
        if hours:
            text += ' '
        last_m = int(str(minutes)[-1:])
        minutes_dict = {
            last_m == 1: 'минута',
            2 <= last_m <= 4: 'минуты',
            last_m >= 5 or last_m == 0: 'минут',
            minutes > 10 and minutes < 20: 'минут'
        }
        text += str(minutes) + ' ' + str(minutes_dict[True])
    if seconds:
        if hours or minutes:
            text += ' '
        last_s = int(str(seconds)[-1:])
        seconds_dict = {
            last_s == 1: 'секунда',
            2 <= last_s <= 4: 'секунды',
            last_s >= 5 or last_s == 0: 'секунд',
            seconds > 10 and seconds < 20: 'секунд'
        }
        text += str(seconds) + ' ' + str(seconds_dict[True])
    return text

#def sleepToExpDateMinusDay(date: str):
#    date = datetime.datetime.fromisoformat(date)
#    exp_date = date + datetime.timedelta(days=30)
#    return datetime.datetime.timestamp(exp_date) - datetime.datetime.timestamp(datetime.datetime.now()) - 14*3600

def textToDatetime(text: str):
    date_time = text.split()
    date = date_time[0].split('-')
    date = date[2] + '-' + date[1] + '-' + date[0]
    if len(date_time) > 1:
        time = date_time[1]
        date_time = date + ' ' + time
    else:
        date_time = date
    return datetime.datetime.fromisoformat(date_time)
    
def monthsAvailabilityCheck(date: str, months):
    date = textToDatetime(date)
    days = months*30
    return datetime.datetime.now() < (date + datetime.timedelta(days=days))

def tarifName(tarif: str):
    if tarif.isdigit():
        if int(tarif) == 1:
            return "Самостоятельный"
        elif int(tarif) == 2:
            return "Хочу большего"
        elif int(tarif) == 3:
            return "Бесплатный пробный период"
        elif int(tarif) == 0:
            return "Не выбран"
    else:
        return "Не выбран"

def dateToDDMMYYYY(date: str):
    if len(date.split()) == 1:
        year, month, day = date.split('-')
        result = f"{day}-{month}-{year}"
    else:
        date, time = date.split()
        year, month, day = date.split('-')
        result = f"{day}-{month}-{year} {time}"
    return result

def datetoYYYYMMDD(date: str):
    if len(date.split()) == 1:
        day, month, year = date.split('-')
        result = f"{year}-{month}-{day}"
    else:
        date, time = date.split()
        day, month, year = date.split('-')
        result = f"{year}-{month}-{day} {time}"
    return result

    