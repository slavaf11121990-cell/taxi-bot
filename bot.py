import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

TOKEN = os.environ.get('VK_TOKEN')

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

print("Бот запущен...")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        text = event.text.lower()
        if 'привет' in text:
            vk.messages.send(
                user_id=event.user_id,
                message='Привет! Я бот-диспетчер Такси ТИЗ (тест).',
                random_id=0
            )
