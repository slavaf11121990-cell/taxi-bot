import os
import sqlite3
import json
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = os.environ.get('VK_TOKEN')
GROUP_ID = 241472407

vk_session = VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY,
            phone TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            user_id INTEGER PRIMARY KEY,
            step TEXT,
            point_from TEXT,
            point_to TEXT,
            seats TEXT,
            day TEXT,
            time TEXT,
            phone TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            point_from TEXT,
            point_to TEXT,
            seats TEXT,
            day TEXT,
            time TEXT,
            phone TEXT,
            status TEXT,
            driver_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🚕 Заказать такси", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🚗 Я водитель", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_cities_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Сибай", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Магнитогорск", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Челябинск", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Екатеринбург", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_seats_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("1 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("2 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("3 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("4 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("СЕДАН", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("МИНИВЭН", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def get_day_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Сегодня", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Завтра", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_time_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("09:00-11:00", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("12:00-14:00", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("15:00-17:00", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("18:00-21:00", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("00:00-02:00", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("03:00-06:00", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_confirm_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("✅ НОМЕР ВЕРНЫЙ", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_take_order_keyboard(order_id):
    keyboard = VkKeyboard(one_time=False, inline=True)
    keyboard.add_button("🎯 ВЗЯТЬ ЗАКАЗ", color=VkKeyboardColor.POSITIVE, payload={"type": "take_order", "order_id": order_id})
    return keyboard.get_keyboard()

def handle_message(user_id, text, payload):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if payload and payload.get("type") == "take_order":
        order_id = payload.get("order_id")
        cursor.execute("SELECT passenger_id, point_from, point_to, phone, status, driver_id FROM orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()

        if order:
            p_id, p_from, p_to, p_phone, status, current_driver = order
            if status == "active":
                cursor.execute("UPDATE orders SET status = 'taken', driver_id = ? WHERE order_id = ?", (user_id, order_id))
                conn.commit()
                send_msg(user_id, f"✅ Вы успешно взяли заказ №{order_id}!\n\n📍 Маршрут: {p_from} -> {p_to}\n📱 ТЕЛЕФОН КЛИЕНТА: {p_phone}\n\nСрочно свяжитесь с пассажиром!")
                send_msg(p_id, "🚕 Водитель принял ваш заказ и уже связывается с вами по указанному телефону!")
            else:
                if current_driver == user_id:
                    send_msg(user_id, "Вы уже взяли этот заказ ранее.")
                else:
                    send_msg(user_id, f"❌ Извините, заказ №{order_id} уже забрал другой водитель!")
        conn.close()
        return

    cursor.execute("SELECT step FROM passengers WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    current_step = res[0] if res else 'main_menu'

    if text.lower() in ["привет", "старт", "начать"]:
        cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'main_menu')", (user_id,))
        conn.commit()
        send_msg(user_id, "Здравствуйте! Это Такси ТИЗ. Выберите:", get_main_keyboard())
        conn.close()
        return

    if text == "🚗 Я водитель":
        cursor.execute("INSERT OR REPLACE INTO drivers (user_id) VALUES (?)", (user_id,))
        conn.commit()
        send_msg(user_id, "Вы успешно зарегистрированы в базе водителей такси ТИЗ! Ожидайте уведомлений о новых заказах.")
        conn.close()
        return

    if text == "🚕 Заказать такси" or text.lower() == "заказать поездку":
        cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'get_from')", (user_id,))
        conn.commit()
        send_msg(user_id, "Откуда вы едете?", get_cities_keyboard())
        conn.close()
        return

    if current_step == 'get_from':
        cursor.execute("UPDATE passengers SET point_from = ?, step = 'get_to' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, "Куда вы едете?", get_cities_keyboard())

    elif current_step == 'get_to':
        cursor.execute("UPDATE passengers SET point_to = ?, step = 'get_seats' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, "СКОЛЬКО ВАС? ЕСЛИ НУЖНА ВСЯ МАШИНА, НАЖМИТЕ СЕДАН ИЛИ МИНИВЭН.", get_seats_keyboard())

    elif current_step == 'get_seats':
        cursor.execute("UPDATE passengers SET seats = ?, step = 'get_day' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, "КОГДА ВЫ ХОТИТЕ ПОЕХАТЬ?", get_day_keyboard())

    elif current_step == 'get_day':
        cursor.execute("UPDATE passengers SET day = ?, step = 'get_time' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, "ВО СКОЛЬКО?", get_time_keyboard())

    elif current_step == 'get_time':
        cursor.execute("UPDATE passengers SET time = ?, step = 'get_phone' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, "ВВЕДИТЕ СВОЙ НОМЕР ТЕЛЕФОНА ДЛЯ СВЯЗИ:")

    elif current_step == 'get_phone':
        cursor.execute("UPDATE passengers SET phone = ?, step = 'confirm_order' WHERE user_id = ?", (text, user_id))
        conn.commit()
        send_msg(user_id, f"Ваш номер: {text}\nВсё верно?", get_confirm_keyboard())

    elif current_step == 'confirm_order' and text == "✅ НОМЕР ВЕРНЫЙ":
        cursor.execute("SELECT point_from, point_to, seats, day, time, phone FROM passengers WHERE user_id = ?", (user_id,))
        p_data = cursor.fetchone()

        if p_data:
            p_from, p_to, p_seats, p_day, p_time, p_phone = p_data
            cursor.execute("INSERT INTO orders (passenger_id, point_from, point_to, seats, day, time, phone, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')",
                           (user_id, p_from, p_to, p_seats, p_day, p_time, p_phone))
            order_id = cursor.lastrowid
            conn.commit()

            send_msg(user_id, "🎉 Спасибо! Ваш заказ отправлен всем свободным водителям. Ждите звонка!", get_main_keyboard())

            cursor.execute("SELECT user_id FROM drivers")
            drivers = cursor.fetchall()
            order_text = (f"📢 НОВЫЙ ЗАКАЗ №{order_id}!\n\n"
                          f"📍 Откуда: {p_from}\n"
                          f"🎯 Куда: {p_to}\n"
                          f"👥 Детали: {p_seats}\n"
                          f"📅 День: {p_day}\n"
                          f"🕐 Время: {p_time}\n\n"
                          f"⚠️ Номер телефона будет доступен после нажатия кнопки!")

            for driver in drivers:
                if driver[0] != user_id:
                    try:
                        send_msg(driver[0], order_text, get_take_order_keyboard(order_id))
                    except:
                        pass

        cursor.execute("UPDATE passengers SET step = 'main_menu' WHERE user_id = ?", (user_id,))
        conn.commit()

    conn.close()

def send_msg(user_id, text, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=text,
        random_id=get_random_id(),
        keyboard=keyboard
    )

if __name__ == "__main__":
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            u_id = event.obj.message['from_id']
            txt = event.obj.message['text']
            p_load = event.obj.message.get('payload')

            if p_load and isinstance(p_load, str):
                try: p_load = json.loads(p_load)
                except: p_load = None

            handle_message(u_id, txt, p_load)
