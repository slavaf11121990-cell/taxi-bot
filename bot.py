import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = os.environ.get('VK_TOKEN')

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

print("Бот запущен...")

# Клавиатура с двумя кнопками
keyboard = VkKeyboard(one_time=False)
keyboard.add_button('Заказать поездку', color=VkKeyboardColor.PRIMARY)
keyboard.add_button('Я водитель', color=VkKeyboardColor.SECONDARY)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        text = event.text.lower()
        if 'привет' in text:
            vk.messages.send(
                user_id=event.user_id,
                message='Привет! Выбери кнопку:',
                keyboard=keyboard.get_keyboard(),
                random_id=0
            )
        elif 'заказать поездку' in text:
            vk.messages.send(
                user_id=event.user_id,
                message='Ты нажал "Заказать поездку".',
                random_id=0
            )
        elif 'я водитель' in text:
            vk.messages.send(
                user_id=event.user_id,
                message='Ты нажал "Я водитель".',
                random_id=0
            )
