import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = os.environ.get('VK_TOKEN')
ADMIN_ID = 572959468

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

print("Бот запущен...")

users = {}

def main_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button('Заказать поездку', color=VkKeyboardColor.PRIMARY)
    kb.add_button('Я водитель', color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def cities_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button('Сибай')
    kb.add_button('Магнитогорск')
    kb.add_button('Челябинск')
    kb.add_button('Екатеринбург')
    return kb.get_keyboard()

def seats_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button('1')
    kb.add_button('2')
    kb.add_button('3')
    kb.add_button('4')
    return kb.get_keyboard()

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        text = event.text.lower().strip()
        user_id = event.user_id

        if text in ['начать', 'start', 'привет']:
            users[user_id] = {'stage': 'main'}
            vk.messages.send(user_id=user_id, message='Здравствуйте! Это Такси ТИЗ. Выберите:', keyboard=main_kb(), random_id=0)

        elif text == 'заказать поездку':
            users[user_id] = {'stage': 'otkuda'}
            vk.messages.send(user_id=user_id, message='Откуда вы едете?', keyboard=cities_kb(), random_id=0)

        elif text == 'я водитель':
            vk.messages.send(user_id=user_id, message='Вы водитель. Введите номер телефона.', random_id=0)

        elif user_id in users:
            stage = users[user_id].get('stage')

            if stage == 'otkuda':
                users[user_id]['otkuda'] = text
                users[user_id]['stage'] = 'kuda'
                vk.messages.send(user_id=user_id, message='Куда вы едете?', keyboard=cities_kb(), random_id=0)

            elif stage == 'kuda':
                users[user_id]['kuda'] = text
                users[user_id]['stage'] = 'mesta'
                vk.messages.send(user_id=user_id, message='Сколько вас?', keyboard=seats_kb(), random_id=0)

            elif stage == 'mesta':
                users[user_id]['mesta'] = text
                users[user_id]['stage'] = 'phone'
                vk.messages.send(user_id=user_id, message='Введите ваш номер телефона:', random_id=0)

            elif stage == 'phone':
                users[user_id]['phone'] = text
                users[user_id]['stage'] = 'done'
                vk.messages.send(user_id=user_id, message='Спасибо! Заказ принят.', random_id=0)
                order = users[user_id]
                vk.messages.send(user_id=ADMIN_ID, message=f"🚖 НОВЫЙ ЗАКАЗ\n\n📍 Откуда: {order['otkuda']}\n🎯 Куда: {order['kuda']}\n👥 Мест: {order['mesta']}\n📞 Телефон: {order['phone']}", random_id=0)
