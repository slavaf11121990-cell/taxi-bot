import os
import sqlite3
import json
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ==========================================
# ПОДКЛЮЧЕНИЕ И НАСТРОЙКА (ДАННЫЕ УСПЕШНО ВНЕСЕНЫ)
# ==========================================
TOKEN = "vk1.a.u5H-G56MAqzOhAwDFEfL1xurn457lPQ4UVh2rqO4xHfDdUcRsrDV1dYBjobxStNAV9m706l7N8z1njjuPQdQrMHS4xElBfzuba9V4yLS288w17bk5odDVdd7TDirNM6eCa5ujzHH7cM-Gv8McvRnllOspvquJaWyjTZEZ7qCR6asCvPaYB6vFoVDHNOiDmyySLeH0PAiLsKUxjaPpsNDMA"
GROUP_ID = 241472407

vk_session = VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# ==========================================
# СОЗДАНИЕ БАЗЫ ДАННЫХ (БЛОКНОТА СЕРВЕРА)
# ==========================================
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Таблица водителей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY,
            phone TEXT
        )
    """)
    # Таблица пассажиров (состояние опроса)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            user_id INTEGER PRIMARY KEY,
            step TEXT,
            point_from TEXT,
            point_to TEXT,
            seats TEXT,
            phone TEXT
        )
    """)
    # Таблица активных заказов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            point_from TEXT,
            point_to TEXT,
            seats TEXT,
            phone TEXT,
            status TEXT,
            driver_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================================
# ШАБЛОНЫ КНОПОК (КЛАВИАТУРЫ)
# ==========================================

# Главное меню
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🚕 Заказать такси", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🚗 Я водитель", color=VkKeyboardColor.GREEN)
    return keyboard.get_keyboard()

# Выбор городов
def get_cities_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Сибай", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Магнитогорск", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Челябинск", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Екатеринбург", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

# Выбор мест
def get_seats_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("1 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("2 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("3 ЧЕЛ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("СЕДАН (Вся машина)", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

# Подтверждение номера
def get_confirm_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("✅ НОМЕР ВЕРНЫЙ", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

# Кнопка «ВЗЯТЬ ЗАКАЗ» для водителей (Инлайн-кнопка под сообщением)
def get_take_order_keyboard(order_id):
    keyboard = VkKeyboard(one_time=False, inline=True)
    keyboard.add_button("🎯 ВЗЯТЬ ЗАКАЗ", color=VkKeyboardColor.POSITIVE, payload={"type": "take_order", "order_id": order_id})
    return keyboard.get_keyboard()

# ==========================================
# ЛОГИКА СВЯЗИ ПАССАЖИРОВ И ВОДИТЕЛЕЙ
# ==========================================

def send_msg(user_id, text, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=text,
        random_id=get_random_id(),
        keyboard=keyboard
    )

def handle_message(user_id, text, payload):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # ПРОВЕРКА НАЖАТИЯ КНОПКИ ВОДИТЕЛЕМ
    if payload and payload.get("type") == "take_order":
        order_id = payload.get("order_id")
        
        cursor.execute("SELECT passenger_id, point_from, point_to, phone, status, driver_id FROM orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()
        
        if order:
            p_id, p_from, p_to, p_phone, status, current_driver = order
            if status == "active":
                cursor.execute("UPDATE orders SET status = 'taken', driver_id = ? WHERE order_id = ?", (user_id, order_id))
                conn.commit()
                
                # Водитель получает скрытый номер телефона пассажира для бабушки!
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
    user_step = cursor.fetchone()
    
    if text.lower() == "привет" or text.lower() == "старт" or not user_step:
        cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'main_menu')", (user_id,))
        conn.commit()
        send_msg(user_id, "Привет! Добро пожаловать в такси МИГ Сибай-Магнитогорск-Челябинск-ЕКБ! Кто вы?", get_main_keyboard())
        
    elif text == "🚗 Я водитель":
        cursor.execute("INSERT OR REPLACE INTO drivers (user_id) VALUES (?)", (user_id,))
        conn.commit()
        send_msg(user_id, "Вы успешно зарегистрированы в базе водителей такси МИГ! Ожидайте уведомлений о новых заказах в этот чат.")
        
    elif text == "🚕 Заказать такси":
        cursor.execute("UPDATE passengers SET step = 'get_from' WHERE user_id = ?", (user_id,))
        conn.commit()
        send_msg(user_id, "ОТКУДА ВЫ ЕДЕТЕ?", get_cities_keyboard())
        
    else:
        step = user_step[0] if user_step else 'main_menu'
        if step == 'get_from':
            cursor.execute("UPDATE passengers SET point_from = ?, step = 'get_to' WHERE user_id = ?", (text, user_id))
            conn.commit()
            send_msg(user_id, "КУДА ВЫ ЕДЕТЕ?", get_cities_keyboard())
            
        elif step == 'get_to':
            cursor.execute("UPDATE passengers SET point_to = ?, step = 'get_seats' WHERE user_id = ?", (text, user_id))
            conn.commit()
            send_msg(user_id, "СКОЛЬКО ВАС? ЕСЛИ НУЖНА ВСЯ МАШИНА, НАЖМИТЕ СЕДАН", get_seats_keyboard())
            
        elif step == 'get_seats':
            cursor.execute("UPDATE passengers SET seats = ?, step = 'get_phone' WHERE user_id = ?", (text, user_id))
            conn.commit()
            send_msg(user_id, "ВВЕДИТЕ СВОЙ НОМЕР ТЕЛЕФОНА ДЛЯ СВЯЗИ (Можно ввести любой номер руками, например для бабушки):")
            
        elif step == 'get_phone':
            cursor.execute("UPDATE passengers SET phone = ?, step = 'confirm_order' WHERE user_id = ?", (text, user_id))
            conn.commit()
            send_msg(user_id, f"Ваш номер: {text}\nВсё верно?", get_confirm_keyboard())
            
        elif step == 'confirm_order' and text == "✅ НОМЕР ВЕРНЫЙ":
            cursor.execute("SELECT point_from, point_to, seats, phone FROM passengers WHERE user_id = ?", (user_id,))
            p_from, p_to, p_seats, p_phone = cursor.fetchone()
            
            cursor.execute("INSERT INTO orders (passenger_id, point_from, point_to, seats, phone, status) VALUES (?, ?, ?, ?, ?, 'active')", 
                           (user_id, p_from, p_to, p_seats, p_phone))
            order_id = cursor.lastrowid
            conn.commit()
            
            send_msg(user_id, "🎉 Спасибо! Ваш заказ отправлен всем свободным водителям. Ждите звонка!", get_main_keyboard())
            
            # РАССЫЛКА ВОДИТЕЛЯМ В ЛИЧКУ
            cursor.execute("SELECT user_id FROM drivers")
            drivers = cursor.fetchall()
            
            order_text = f"📢 НОВЫЙ ЗАКАЗ №{order_id}!\n\n📍 Откуда: {p_from}\n📍 Куда: {p_to}\n👥 Места: {p_seats}\n\n⚠️ Номер телефона будет доступен после нажатия кнопки!"
            
            for driver in drivers:
                try:
                    send_msg(driver[0], order_text, get_take_order_keyboard(order_id))
                except:
                    pass
                    
            cursor.execute("UPDATE passengers SET step = 'main_menu' WHERE user_id = ?", (user_id,))
            conn.commit()

    conn.close()

# ==========================================
# ГЛАВНЫЙ ЦИКЛ ОПРОСА
# ==========================================
print("Бот Диспетчерская Такси МИГ успешно запущен!")
for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        u_id = event.obj.message['from_id']
        txt = event.obj.message['text']
        p_load = event.obj.message.get('payload')
        
        if p_load and isinstance(p_load, str):
            try: p_load = json.loads(p_load)
            except: p_load = None
            
        handle_message(u_id, txt, p_load)
