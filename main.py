from db_functions import check_DB, get_DB, Upsert_DB
from db_functions import Bot_status, Messages_DB, DB_queries
from handlers import MessageHandler, str_transform
from keyboard import keyboard_menu, keyboard_begin
from messages import message_codes, no_message_code
from messages import bot_activation, get_users_nobot
from messages import bot_command_on, bot_off_command
from messages import correction_text, adv_phrases, adv_answer
import requests
from settings import admin_id
from vk_api.bot_longpoll import VkBotEventType
from vk_functions import VKMethods


longpoll = VKMethods.Bot_longpoll()

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                '''
                Для избежания ошибочного ввода команд пользователями проводим корректировку
                вводимого пользователями текста, исключая лишние символы и через словарь correction_text
                задаём соответствие ошибочных и корректных команд.
                '''
                incoming_text = str(event.obj.message['text'])
                incoming_text = incoming_text.lower().replace("'", "") \
                                             .replace("\"", "") \
                                             .replace("«", "").replace("»", "")
                message_from_user = correction_text.get(incoming_text, incoming_text).capitalize()

                '''
                Далее определяем порядок обработки полученной вместе с новым сообщением информации
                '''
                if event.from_user:
                    attachments = list(event.obj.message['attachments'])  # передаём в список набор прикреплённых к сообщению объектов
                    forward = list(event.obj.message['fwd_messages'])  # передаём в список набор прикреплённых к сообщению пересланных сообщений
                    vk_id = int(event.obj.message['from_id'])  # сохраняем в переменную ВК id пользователя

                    '''
                    Для дальнейшего анализа диалогов и воронки чат-бота необходимо сохранять сообщения пользователей.
                    Для этого каждой предустановленной команде и сообщению бота присвоены короткие коды.
                    Каждое новое сообщение пользователя сопоставляется с этими кодами и итоговый код сообщения сохраняется в переменную.
                    '''
                    msg_code = message_codes.get(message_from_user, no_message_code)
                    user_id = get_DB.get_user_id(vk_id)  # получаемый id пользователя из нашей БД

                    '''
                    Сценарий использования бота предполагает, что через бота пользователь оформляет заказ, а затем, в том же диалоге
                    общается с администратором группы по поводу деталей, где сообщения уже нетиповые.
                    Поэтому необходимо иметь возможность "включать" и "выключать" бота для конкретного пользователя.
                    '''
                    bot_off = check_DB.check_bot_off(user_id)  # проверяем, выключен ли бот для данного пользователя
                    Messages_DB.add_incoming_msg(user_id, msg_code)  # добавляем сообщение от пользователя в БД

                    '''
                    Администраторов групп часто спамят рекламными сообщениями от других ботов.
                    Бот ищет наличие ключевых слов, характеризующих подобные сообщения и если находит хотя бы одно от пользователя,
                    который ранее не писал в группу, то отправляет пользователю предупреждение, что его сообщение идентифицировано как спам,
                    не добавляя пользователя в БД.
                    '''
                    adv_words = [phrase for phrase in adv_phrases if (phrase in message_from_user)]  # находим все слова, указывающие на спам
                    if bool(adv_words) is True and user_id is None:
                        VKMethods.send_msg('user_id', vk_id, user_id, adv_answer, keyboard_menu)  # отправляем предупреждение
                        break

                    '''
                    Частая задача для администратора - получить список пользователей, для которых бот "выключен". Чтобы не
                    ходить напрямую в БД, для этого реализована команда боту. Если сообщение получено от администратора и сообщение
                    совпадает с этой командой, то производится запрос в БД и бот отдаёт список таких пользователей.
                    '''
                    if (vk_id == int(admin_id)) and (message_from_user == get_users_nobot):
                        nobot = DB_queries.get_users_bot_off()  # получаем список всех пользователей, у которых бот выключен
                        VKMethods.send_msg('user_id', vk_id, user_id, '\n'.join(nobot), keyboard_menu)  # передаём полученный список в сообщении

                    '''
                    Пользователи обычно начинают диалог с команды "Начать". При получении этой команды бот отвечает приветственным сообщением,
                    а также добавляет пользователя в БД, если он является новым.
                    Если эта команда была отправлена, когда бот был "выключен", то, получив её, он снова "включается" и реагирует на все сообщения.
                    Если же пользователи отправляют другие сообщения, не совпадающие с командой активации, то это сообщение передаётся в
                    обработчик, код которого написан в файле handlers.py
                    '''
                    if bot_off is False and str_transform(message_from_user) in bot_command_on:
                        user_names = VKMethods.get_user(vk_id)
                        user_name = user_names[0]['first_name'] + ' ' + user_names[0]['last_name']
                        Upsert_DB.add_user(vk_id, user_name)
                        VKMethods.send_msg('user_id', vk_id, user_id, bot_activation, keyboard_begin)
                    elif str_transform(message_from_user) in bot_command_on:
                        Bot_status.turn_on(message_from_user, user_id)
                        VKMethods.send_msg('user_id', vk_id, user_id, bot_activation, keyboard_begin)
                    elif bot_off is False:
                        MessageHandler.answer_to_user(message_from_user, vk_id, user_id, forward, attachments)

            elif event.type == VkBotEventType.MESSAGE_REPLY:
                '''
                Администратор может включить или выключить бота командой, находясь в чате с пользователем. Для реализации этой
                возможности используется код, представленный ниже.
                '''
                user_id = get_DB.get_user_id(event.obj.peer_id)  # получаем id пользователя, в чат с которым отправлено сообщение
                if (event.obj.peer_id != int(admin_id)) and (str_transform(event.obj.text) in bot_command_on):
                    Bot_status.turn_on(event.obj.text, user_id)  # включаем бота, если отправленное сообщение соответствует этой команде
                    VKMethods.send_msg('user_id', event.obj.peer_id, user_id, bot_activation, keyboard_menu)  # отправляем приветственное сообщение от бота
                elif (str_transform(event.obj.text) == bot_off_command):
                    Bot_status.turn_off_by_command(event.obj.text, user_id)   # выключаем бота, если получена соответствующая команда

            elif event.type == VkBotEventType.MESSAGE_DENY:
                '''
                Пользователи часто запрещают отправку сообщений боту. При этом у них может остаться незавершённым оформление заказа,
                либо бот может быть "выключен".
                Код, представленный ниже, подчищает эти "хвосты" - завершает все открытые заказы пользователя и "включает" бота в случае,
                если пользователь запретил сообщения, т.е. прервал коммуникацию.
                '''
                user_id = get_DB.get_user_id(event.obj.user_id)  # получаем id пользователя
                opened_order_id = get_DB.get_opened_order(user_id)  # получаем id открытых заказов
                Upsert_DB.cancel_order(opened_order_id)  # отменяем открытые заказы
                if check_DB.check_bot_off(user_id) is True:
                    Bot_status.turn_on(bot_command_on[0], user_id)  # включаем бота, если он был выключен

    except (KeyboardInterrupt, SystemExit):
        raise
    except requests.exceptions.ReadTimeout:
        continue
    except requests.exceptions.ConnectionError:
        print("Connection Error")
    except Exception:
        print("Catched an exception!")
        raise
