from db_functions import Messages_DB
from messages import message_codes, no_message_code
from messages import message_to_admin_code
import settings
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.utils import get_random_id

'''
У ВК существует ограничение на максимальное количество символов в сообщении.
Бот объединяет информацию из нескольких сообщений, поэтому для того, чтобы она передавалась
корректно, необходимо задать максимальную длину сообщения.
'''
message_limit = int(4000)


# класс функций для упрощения обращения к методам API ВК
class VKMethods():
    session = VkApi(token=settings.token)

    # подключение к longpoll серверу
    @classmethod
    def Bot_longpoll(cls):
        return VkBotLongPoll(VKMethods.session, settings.group_id, wait=60)

    # получение информации о пользователе по его id
    @classmethod
    def get_user(cls, user_id: int):
        user_info = cls.session.method('users.get', {'user_ids': user_id})
        return user_info

    # отправка сообщения пользователю
    @classmethod
    def send_msg(cls, id_type, vk_id: int, user_id: int, msg_to_user: str, keyboard=None,
                 attachment=None):
        cls.session.method('messages.send',
                           {id_type: vk_id,
                            'message': msg_to_user,
                            'random_id': get_random_id(),
                            'attachment': attachment,
                            'keyboard': keyboard(),
                            'dont_parse_links': 1  # параметр, ограничивающий чтение заголовков ссылок в сообщении
                            }
                           )
        if vk_id == settings.admin_id:
            msg_code = message_codes.get(msg_to_user, message_to_admin_code)
        else:
            msg_code = message_codes.get(msg_to_user, no_message_code)
        Messages_DB.add_outcoming_msg(user_id, msg_code)  # добавление в БД исходящего сообщения


# класс функций для упрощения работы с сообщениями, содержащими прикреплённые объекты
class VK_attachments():

    '''
    Бот ВК предполагает работу в сообществах, в которых ТЗ может быть описано текстом, либо приложено в виде фото или файла.
    Сообщения с другими типами прикреплённых объектов должны быть идентифицированы, чтобы выводить предупреждение пользователю.
    '''
    @staticmethod
    def attach_not_files(attachment: list):
        try:
            for i in attachment:
                if i['type'] != 'doc' and i['type'] != 'photo':
                    return True
        except TypeError:
            return False

    '''
    Информация о каждом прикреплённом к сообщению объекте возвращается в виде многоуровневого словаря. Чтобы бот мог присоединить эти
    прикрепления к своему сообщению для администратора, необходимо его обработать, выбрав только необходимые параметры.

    Функция ниже отвечает за обработку прикреплений и определение прямой ссылки на каждый прикреплённый объект для тех типов
    прикреплённых объектов, которые допустимо присылать (фото и файлы). Эти объекты будут прикреплены к сообщению, отправляемому от
    бота администратору.
    '''
    @staticmethod
    def attach_for_send(attachment: list):
        address = []
        for i in attachment:
            if i['type'] == 'doc':
                owner_id = i['doc']['owner_id']
                id = i['doc']['id']
                access_key = i['doc']['access_key']
                address.append(f'doc{owner_id}_{id}_{access_key}')
            elif i['type'] == 'photo':
                owner_id = i['photo']['owner_id']
                id = i['photo']['id']
                access_key = i['photo']['access_key']
                address.append(f'photo{owner_id}_{id}_{access_key}')
        link = ",".join(address)
        return link

    '''
    Все прикреплённые в процессе оформления заказа файлы необходимо собрать в одно сообщение, которое отправить
    администратору. Функция ниже отвечает за формирование сообщения, содержащего ссылки на прикрепления прямо в тексте,
    чтобы по ним можно было напрямую перейти к объектам. Данный способ является альтернативой прикреплению файла,
    который используется в предыдущей функции.
    '''
    @staticmethod
    def attach_links(attachment: list):
        address = []
        step = 0
        for i in attachment:
            step += 1
            if i['type'] == 'doc':
                url_doc = i['doc']['url']
                address.append(f'Файл {step} (документ):{url_doc}')
            elif i['type'] == 'photo':
                sizes = i['photo']['sizes']
                sizes_height = []
                for j in sizes:
                    sizes_height.append(int(j['height']))
                max_height = max(sizes_height)
                max_size = sizes_height.index(max_height)
                url_photo = i['photo']['sizes'][max_size]['url']
                address.append(f'Файл {step} (фото): {url_photo}')
        link = "\n".join(address)
        return link
