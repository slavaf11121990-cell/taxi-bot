import os
import re
import sqlite3
import json
from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = os.environ.get('VK_TOKEN')
GROUP_ID = 241472407
ADMIN_ID = 572959468

vk_session = VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

CITIES = ["Сибай", "Магнитогорск", "Челябинск", "Екатеринбург"]
SEATS = ["1 человек", "2 человека", "3 человека", "4 человека",
         "5 человек", "6 человек", "7 человек", "8 человек",
         "Легковое такси", "Минивэн"]
DAYS = ["Сегодня", "Завтра", "Послезавтра"]
TIMES = ["09:00-11:00", "12:00-14:00", "15:00-17:00", "18:00-21:00", "00:00-02:00", "03:00-06:00"]

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS drivers (user_id INTEGER PRIMARY KEY, phone TEXT)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            user_id INTEGER PRIMARY KEY, step TEXT, point_from TEXT, point_to TEXT,
            seats TEXT, day TEXT, time TEXT, phone TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT, passenger_id INTEGER,
            point_from TEXT, point_to TEXT, seats TEXT, day TEXT, time TEXT,
            phone TEXT, status TEXT, driver_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def main_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("🚕 Заказать такси", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🚗 Я водитель", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()

def cities_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("Сибай", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Магнитогорск", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Челябинск", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Екатеринбург", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def seats_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("1 человек", color=VkKeyboardColor.SECONDARY)
    kb.add_button("2 человека", color=VkKeyboardColor.SECONDARY)
    kb.add_button("3 человека", color=VkKeyboardColor.SECONDARY)
    kb.add_button("4 человека", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("5 человек", color=VkKeyboardColor.SECONDARY)
    kb.add_button("6 человек", color=VkKeyboardColor.SECONDARY)
    kb.add_button("7 человек", color=VkKeyboardColor.SECONDARY)
    kb.add_button("8 человек", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Легковое такси", color=VkKeyboardColor.PRIMARY)
    kb.add_button("Минивэн", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()

def day_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("Сегодня", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Завтра", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def time_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("09:00-11:00", color=VkKeyboardColor.SECONDARY)
    kb.add_button("12:00-14:00", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("15:00-17:00", color=VkKeyboardColor.SECONDARY)
    kb.add_button("18:00-21:00", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("00:00-02:00", color=VkKeyboardColor.SECONDARY)
    kb.add_button("03:00-06:00", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def confirm_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("✅ НОМЕР ВЕРНЫЙ", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()

def passenger_actions_kb(order_id):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("❌ Отказаться от поездки", color=VkKeyboardColor.NEGATIVE, payload={"type": "cancel_trip", "order_id": order_id})
    kb.add_line()
    kb.add_button("⚠️ Водитель не позвонил", color=VkKeyboardColor.SECONDARY, payload={"type": "driver_no_call", "order_id": order_id})
    kb.add_line()
    kb.add_button("📩 Пожаловаться", color=VkKeyboardColor.PRIMARY, payload={"type": "complaint", "order_id": order_id})
    return kb.get_keyboard()

def driver_actions_kb(order_id):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("❌ Отказаться от заказа", color=VkKeyboardColor.NEGATIVE, payload={"type": "driver_cancel", "order_id": order_id})
    kb.add_line()
    kb.add_button("📩 Пожаловаться", color=VkKeyboardColor.PRIMARY, payload={"type": "complaint", "order_id": order_id})
    return kb.get_keyboard()

def take_order_kb(order_id):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("🎯 ВЗЯТЬ ЗАКАЗ", color=VkKeyboardColor.POSITIVE, payload={"type": "take_order", "order_id": order_id})
    return kb.get_keyboard()

def send_msg(user_id, text, keyboard=None):
    vk.messages.send(user_id=user_id, message=text, random_id=get_random_id(), keyboard=keyboard)

def broadcast_order(cursor, order_id):
    cursor.execute("SELECT point_from, point_to, seats, day, time FROM orders WHERE order_id = ?", (order_id,))
    o = cursor.fetchone()
    if not o:
        return
    p_from, p_to, p_seats, p_day, p_time = o
    order_text = (f"📢 НОВЫЙ ЗАКАЗ №{order_id}!\n\n"
                  f"📍 Откуда: {p_from}\n🎯 Куда: {p_to}\n"
                  f"👥 Детали: {p_seats}\n📅 День: {p_day}\n🕐 Время: {p_time}\n\n"
                  f"⚠️ Номер телефона будет доступен после нажатия кнопки!")
    cursor.execute("SELECT user_id FROM drivers")
    for d in cursor.fetchall():
        try:
            send_msg(d[0], order_text, take_order_kb(order_id))
        except:
            pass

def handle_message(user_id, text, payload):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if payload:
        ptype = payload.get("type")
        oid = payload.get("order_id")

        if ptype == "take_order":
            cursor.execute("SELECT passenger_id, point_from, point_to, phone, status, driver_id FROM orders WHERE order_id = ?", (oid,))
            o = cursor.fetchone()
            if o:
                p_id, p_from, p_to, p_phone, status, cur_drv = o
                if status == "active":
                    cursor.execute("UPDATE orders SET status='taken', driver_id=? WHERE order_id=?", (user_id, oid))
                    conn.commit()
                    send_msg(user_id, f"✅ Вы взяли заказ №{oid}!\n\n📍 {p_from} -> {p_to}\n📱 ТЕЛЕФОН: {p_phone}", driver_actions_kb(oid))
                    send_msg(p_id, "🚕 Водитель принял заказ! Ожидайте звонка.", passenger_actions_kb(oid))
                elif cur_drv == user_id:
                    send_msg(user_id, "Вы уже взяли этот заказ.")
                else:
                    send_msg(user_id, f"❌ Заказ №{oid} уже забрал другой водитель!")
            conn.close()
            return

        if ptype == "cancel_trip":
            cursor.execute("SELECT passenger_id, driver_id FROM orders WHERE order_id=?", (oid,))
            o = cursor.fetchone()
            if o:
                p_id, d_id = o
                if p_id == user_id:
                    cursor.execute("UPDATE orders SET status='cancelled' WHERE order_id=?", (oid,))
                    conn.commit()
                    send_msg(user_id, "❌ Вы отменили поездку.", main_kb())
                    if d_id:
                        send_msg(d_id, f"❌ Пассажир отменил заказ №{oid}.")
            conn.close()
            return

        if ptype == "driver_no_call":
            cursor.execute("SELECT passenger_id, driver_id FROM orders WHERE order_id=?", (oid,))
            o = cursor.fetchone()
            if o:
                p_id, d_id = o
                if p_id == user_id:
                    cursor.execute("UPDATE orders SET status='active', driver_id=NULL WHERE order_id=?", (oid,))
                    conn.commit()
                    send_msg(user_id, "Заказ возвращён в поиск. Ждите другого водителя.")
                    if d_id:
                        send_msg(d_id, f"⚠️ Пассажир сообщил, что вы не позвонили. Заказ №{oid} возвращён в поиск.")
                    broadcast_order(cursor, oid)
            conn.close()
            return

        if ptype == "driver_cancel":
            cursor.execute("SELECT passenger_id, driver_id FROM orders WHERE order_id=?", (oid,))
            o = cursor.fetchone()
            if o:
                p_id, d_id = o
                if d_id == user_id:
                    cursor.execute("UPDATE orders SET status='active', driver_id=NULL WHERE order_id=?", (oid,))
                    conn.commit()
                    send_msg(user_id, "❌ Вы отказались от заказа.", main_kb())
                    send_msg(p_id, "⚠️ Водитель отказался от заказа. Ищем другого.")
                    broadcast_order(cursor, oid)
            conn.close()
            return

        if ptype == "complaint":
            cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'complaint')", (user_id,))
            conn.commit()
            send_msg(user_id, "📩 Опишите проблему одним сообщением. Мы разберёмся.")
            conn.close()
            return

    cursor.execute("SELECT step FROM passengers WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    step = res[0] if res else 'main_menu'

    if text.lower() in ["привет", "старт", "начать"]:
        cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'main_menu')", (user_id,))
        conn.commit()
        send_msg(user_id, "Здравствуйте! Это Такси ТИЗ. Выберите:", main_kb())
        conn.close()
        return

    if text == "🚗 Я водитель":
        cursor.execute("INSERT OR REPLACE INTO drivers (user_id) VALUES (?)", (user_id,))
        conn.commit()
        send_msg(user_id, "✅ Вы зарегистрированы как водитель. Ожидайте заказы.")
        conn.close()
        return

    if text == "🚕 Заказать такси":
        cursor.execute("INSERT OR REPLACE INTO passengers (user_id, step) VALUES (?, 'get_from')", (user_id,))
        conn.commit()
        send_msg(user_id, "Откуда вы едете?", cities_kb())
        conn.close()
        return

    if step == 'get_from':
        if text not in CITIES:
            send_msg(user_id, "Пожалуйста, выберите город из кнопок:", cities_kb())
            conn.close()
            return
        cursor.execute("UPDATE passengers SET point_from=?, step='get_to' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, "Куда вы едете?", cities_kb())

    elif step == 'get_to':
        if text not in CITIES:
            send_msg(user_id, "Пожалуйста, выберите город из кнопок:", cities_kb())
            conn.close()
            return
        cursor.execute("SELECT point_from FROM passengers WHERE user_id=?", (user_id,))
        from_city = cursor.fetchone()[0]
        if text == from_city:
            send_msg(user_id, f"❌ Откуда и куда не могут совпадать. Вы уже едете из «{from_city}». Выберите другой город:", cities_kb())
            conn.close()
            return
        cursor.execute("UPDATE passengers SET point_to=?, step='get_seats' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, "Сколько вас поедет?\nЕсли хотите заказать машину целиком — нажмите «Легковое такси» или «Минивэн».", seats_kb())

    elif step == 'get_seats':
        if text not in SEATS:
            send_msg(user_id, "Пожалуйста, выберите из кнопок:", seats_kb())
            conn.close()
            return
        cursor.execute("UPDATE passengers SET seats=?, step='get_day' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, "КОГДА ВЫ ХОТИТЕ ПОЕХАТЬ?", day_kb())

    elif step == 'get_day':
        if text not in DAYS:
            send_msg(user_id, "Пожалуйста, выберите из кнопок:", day_kb())
            conn.close()
            return
        cursor.execute("UPDATE passengers SET day=?, step='get_time' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, "ВО СКОЛЬКО?", time_kb())

    elif step == 'get_time':
        if text not in TIMES:
            send_msg(user_id, "Пожалуйста, выберите интервал из кнопок:", time_kb())
            conn.close()
            return
        cursor.execute("UPDATE passengers SET time=?, step='get_phone' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, "ВВЕДИТЕ НОМЕР ТЕЛЕФОНА в формате +7XXXXXXXXXX или 8XXXXXXXXXX:")

    elif step == 'get_phone':
        if not re.match(r'^(\+7|7|8)\d{10}$', text.replace(" ", "").replace("-", "")):
            send_msg(user_id, "❌ Неверный формат. Введите номер: +7XXXXXXXXXX или 8XXXXXXXXXX")
            conn.close()
            return
        cursor.execute("UPDATE passengers SET phone=?, step='confirm_order' WHERE user_id=?", (text, user_id))
        conn.commit()
        send_msg(user_id, f"Ваш номер: {text}\nВсё верно?", confirm_kb())

    elif step == 'confirm_order' and text == "✅ НОМЕР ВЕРНЫЙ":
        cursor.execute("SELECT point_from, point_to, seats, day, time, phone FROM passengers WHERE user_id=?", (user_id,))
        p = cursor.fetchone()
        if p:
            p_from, p_to, p_seats, p_day, p_time, p_phone = p
            cursor.execute("INSERT INTO orders (passenger_id, point_from, point_to, seats, day, time, phone, status) VALUES (?,?,?,?,?,?,?,'active')",
                           (user_id, p_from, p_to, p_seats, p_day, p_time, p_phone))
            oid = cursor.lastrowid
            conn.commit()
            send_msg(user_id, "🎉 Заказ отправлен водителям! Ждите звонка.", main_kb())
            broadcast_order(cursor, oid)
        cursor.execute("UPDATE passengers SET step='main_menu' WHERE user_id=?", (user_id,))
        conn.commit()

    elif step == 'complaint':
        send_msg(ADMIN_ID, f"📩 ЖАЛОБА от {user_id}:\n\n{text}")
        send_msg(user_id, "✅ Спасибо! Жалоба отправлена администратору.", main_kb())
        cursor.execute("UPDATE passengers SET step='main_menu' WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()

if __name__ == "__main__":
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            u_id = event.obj.message['from_id']
            txt = event.obj.message['text']
            p_load = event.obj.message.get('payload')
            if p_load and isinstance(p_load, str):
                try:
                    p_load = json.loads(p_load)
                except:
                    p_load = None
            handle_message(u_id, txt, p_load)
