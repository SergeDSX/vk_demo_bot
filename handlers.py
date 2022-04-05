from datetime import datetime as dt
from db_functions import check_DB, get_DB, Upsert_DB, Bot_status
from db_models import Order
import json
from keyboard import keyboard_choice, keyboard_empty
from messages import answer, keyboard_command, bot_command_on
from messages import steps, order_command, translate_from_db, bot_grade
from settings import admin_id, group_id
import time
from vk_functions import VKMethods, VK_attachments, message_limit


# функция обработки текстов для получения корректных команд в случае, если они введены с ошибкой
def str_transform(string: str):
    return string.lower().strip().capitalize()


class CheckConditions():

    '''
    Для направления пользователя на ту или иную ветку необходима проверка ряда условий.
    В данном классе объединяются все условия, которые проверяются прежде, чем связанные с ними
    команды будут выполнены. Это проверки действий пользователей: дают ли они команду с клавиатуры,
    дают ли они команду на отмену заказа, на создание заказа или вызов администратора, а также проверка
    того, является ли их сообщение первым. В названии функции отражено её назначение.
    '''

    @staticmethod
    def check_keyboard_command(message_from_user: str):
        return bool(message_from_user in keyboard_command.values() or
                    message_from_user in order_command.values())

    @staticmethod
    def check_cancel_order(message_from_user: str):
        return bool(message_from_user == keyboard_command["cancel"])

    @staticmethod
    def check_create_order(message_from_user: str):
        return bool(message_from_user in order_command.values())

    @staticmethod
    def check_admin_call(message_from_user: str):
        return bool(message_from_user == keyboard_command["admin_menu_2"])

    @staticmethod
    def check_first_message(message_from_user: str, user_id: int, vk_id: int,
                            check_opened_orders: bool):
        if (check_opened_orders is False) and (
           (check_DB.check_old_user(vk_id) is False)):
            return True


class OrderCommands():

    '''
    В данном классе объединены команды работы с заказами: команда на создание заказа и на его отмену.
    В названии функции отражено её назначение. Данные команды объединены в отдельный класс, поскольку связаны с ветками диалога.
    Команда на создание заказа переводит диалога из режима "меню" в режим "заполнения анкеты", а команда на отмену заказа
    переводит бота обратно в режим "меню".
    '''

    @staticmethod
    def start_new_order(message_from_user: str, user_id: int):
        orders = {
            order_command["standard"]: Upsert_DB.add_order_standard_online,
            order_command["cdo"]: Upsert_DB.add_order_cdo_online,
            order_command["off_standard"]: Upsert_DB.add_order_standard_offline,
            order_command["off_cdo"]: Upsert_DB.add_order_cdo_offline}

        if message_from_user in orders:
            return orders.get(message_from_user)(user_id)

    @staticmethod
    def cancel_order(message_from_user: str, order_id: int):
        if CheckConditions.check_cancel_order(message_from_user) is True:
            Upsert_DB.cancel_order(order_id)


class MessageHandler():

    '''
    В этом классе объединены функции, отвечающие за обработку сообщений и выбор ответов, а также ветвление диалога.

    send_message_choice - отвечает за выбор ветки, по которой направить пользователя (один из следующих трёх).

    first_message_handler - добавляет пользователя в БД, если пользователь новый, а также отвечает на первое сообщение
    от пользователя, либо на сообщение, соответствующее переходу в начало диалога / в главное меню.

    command_before_order - осуществляет навигацию между пунктами меню, опцией создания нового заказа и
    опцией выбора связи с администратором. Для каждой из веток выбирается своё ответное сообщение.

    command_order_process - ограничивает при переходе по шагам оформления заказа возможности применения команд,
    относящихся к другим веткам чат-бота и выводит сообщение об ошибке в случае их использования. Допускает лишь свободный
    ответ на вопросы анкеты, либо команду отмены заказа.

    order_processing - осуществляет последовательное заполнение анкеты (спецификации заказа) информацией от пользователя
    с помощью цикла по ключам словаря, соответствующего количеству вопросов. На каждом шаге в цикле проверяется, является ли
    значение словаря соответствующего шага анкеты пустым, и если нет, то переходит к следующему шагу, а если да, то выводит
    пользователю сообщение с вопросом из анкеты.

    attachment_reaction и forward_reaction - регулируют корректное использование перепостов и прикреплений к сообщению
    (они допустимы только при оформлении заказа, в остальных случаев для навигации используются команды бота).

    answer_to_user - аккумулирует результаты работы предыдущих функций, сохраняя ответ, который должен быть передан пользователю,
    а также клавиатуру, которая должна быть присоединена к этому сообщению, и передаёт их через VK API.

    send_to_admin - специальная функция, которая собирает из БД полученные данные из спецификации заказа и отправляет их
    админу в одном сообщении по заранее определённой форме.
    '''

    @classmethod
    def first_message_handler(cls, message_from_user: str, vk_id: int):
        if check_DB.check_old_user(vk_id) is False:
            user_names = VKMethods.get_user(vk_id)
            user_name = user_names[0]['first_name'] + ' ' + user_names[0]['last_name']
            Upsert_DB.add_user(vk_id, user_name)
            return answer.get("1st_message_new_client")
        else:
            return answer.get("1st_message_old_client")

    @classmethod
    def command_before_order(cls, message_from_user: str, user_id: int):
        if CheckConditions.check_create_order(str_transform(message_from_user)) is True:
            OrderCommands.start_new_order(str_transform(message_from_user), user_id)
            return answer["order_process"].get(str_transform(message_from_user))
        elif CheckConditions.check_admin_call(str_transform(message_from_user)) is True:
            Bot_status.turn_off_call_admin(user_id)
            return answer["before_order"].get(str_transform(message_from_user), answer["unknown_command"])
        else:
            return answer["before_order"].get(str_transform(message_from_user), answer["unknown_command"])

    @classmethod
    def command_order_process(cls, message_from_user: str, vk_id: int, user_id: int,
                              forward: list, attachment: list):
        opened_order_id = get_DB.get_opened_order(user_id)
        if CheckConditions.check_keyboard_command(str_transform(message_from_user)) is True:
            if CheckConditions.check_cancel_order(str_transform(message_from_user)) is True:
                OrderCommands.cancel_order(str_transform(message_from_user), opened_order_id)
                return answer["order_process"].get(str_transform(
                    keyboard_command["cancel"]), answer["incorrect_command"])
            else:
                return answer["incorrect_command"]
        else:
            return cls.order_processing(message_from_user, vk_id, user_id,
                                        forward, attachment, opened_order_id)

    @classmethod
    def send_message_choice(cls, message_from_user: str, vk_id: int, user_id: int,
                            forward: list, attachment: list, check_opened_orders: bool):
        if CheckConditions.check_first_message(message_from_user,
                                               user_id, vk_id, check_opened_orders) is True:
            return cls.first_message_handler(message_from_user, vk_id)
        else:
            if check_opened_orders is True:
                return cls.command_order_process(message_from_user, vk_id, user_id, forward, attachment)
            else:
                return cls.command_before_order(message_from_user, user_id)

    @classmethod
    def order_processing(cls, message_from_user: str, vk_id: int, user_id: int,
                         forward: list, attachment: list, opened_order_id: int):
        last_order_id = get_DB.get_last_order(user_id)
        if bool(forward) is True:
            Upsert_DB.mark_forward(last_order_id)

        if str_transform(message_from_user) in bot_command_on:
            message_to_user = answer["incorrect_command"]
            return message_to_user
        else:
            order_parameters = {"standard":
                                    {
                                        "second_message": None,
                                        "format": None,
                                        "time_limit": None,
                                        "time_and_date": None
                                    },
                                "cdo":
                                    {
                                        "second_message": None,
                                        "format": None,
                                        "time_limit": None,
                                        "time_and_date": None
                                    },
                                "off_standard":
                                    {
                                        "second_message": None,
                                        "format": None,
                                        "time_limit": None,
                                        "time_and_date": None
                                    },
                                "off_cdo":
                                    {
                                        "second_message": None,
                                        "format": None,
                                        "time_limit": None,
                                        "time_and_date": None
                                    }
                                }
            description = check_DB.check_empty_description(opened_order_id)
            order_subtype = get_DB.get_order_subtype(opened_order_id)

            # здесь создаётся placeholder для случая, когда пользователь отправил перепост
            # или прикрепил документ без сообщения, чтобы в информации для админа не было пустого сообщения
            if (message_from_user == "" and bool(forward) is True) or \
               (message_from_user == "" and bool(attachment) is True):
                message_from_user = "Пересланное сообщение или файл без сообщения"

            # при заполнении анкеты сначала проверяем, заполнено ли описание хотя бы частично
            # если нет, то выбираем тот тип заказа, спецификацию которого будем заполнять и
            # заполняем ответ на первый вопрос, а также сохраняем перепосты с прикреплениями
            if description is False:
                parameters = order_parameters[order_subtype]
                parameters["second_message"] = message_from_user
                final_parameters = json.dumps(parameters)
                media = json.dumps(attachment)
                message_to_user = steps[order_subtype]["second_message"]
                Upsert_DB.add_order_description(opened_order_id, final_parameters)
                Upsert_DB.add_order_attachment(opened_order_id, media)
                return message_to_user

            # если описание заполнено, то определяем последний шаг, для которого оно не заполнено,
            # и заполняем этот шаг в соответствии с информацией, которая для него требуется
            # при этом также выгружаем json с прикреплениями из предыдущих шагов и дополняем его
            # прикреплениями с текущего шага
            else:
                parameters = json.loads(get_DB.get_order_description(opened_order_id))
                media = json.loads(get_DB.get_order_attachment(opened_order_id))
                if media is None:
                    media = []

                if bool(list(parameters.values()).count(None)) is True:
                    for i in parameters:
                        if parameters[i] is None:
                            parameters[i] = message_from_user
                            media.extend(attachment)
                            message_to_user = steps[order_subtype][i]
                            final_parameters = json.dumps(parameters)
                            final_media = json.dumps(media)
                            Upsert_DB.add_order_description(opened_order_id, final_parameters)
                            Upsert_DB.add_order_attachment(opened_order_id, final_media)
                            return message_to_user
                            break

                # когда не останется незаполненных полей, переходим к заполнению
                # информации о сроках и комментариях, отправляем завершающее сообщение и "выключаем" бота
                else:
                    if check_DB.check_order_deadline(opened_order_id) is False:
                        Upsert_DB.add_order_deadline(opened_order_id, message_from_user)
                        message_to_user = steps["deadline"]
                        return message_to_user

                    else:
                        if check_DB.check_order_comments(opened_order_id) is False:
                            Upsert_DB.add_order_comments(opened_order_id, message_from_user)
                            Upsert_DB.finish_order(opened_order_id)
                            if check_DB.check_correct_order(last_order_id) is True:
                                message_to_user = steps["finish_order"]
                                Upsert_DB.sended_mark_on(last_order_id)
                                Bot_status.turn_off(user_id, last_order_id)
                                cls.send_to_admin(user_id, vk_id, last_order_id)
                                return message_to_user
                            else:
                                message_to_user = answer["error_DB"]
                                Bot_status.turn_off(user_id, last_order_id)
                                cls.send_to_admin(user_id, vk_id, last_order_id)
                                return message_to_user

    '''
    в ответе пользователю сначала выводятся реакции на перепост или прикрепление
    в ветке, в которой это не предусмотрено, а затем уже непосредственная реакция на
    само сообщение пользователя
    при этом дополнительно пользователю отправляется сообщение с запросом оценки бота,
    если он прошёл последний шаг оформления заказа
    пауза (time sleep) используется там, где предполагается отправка нескольких сообщений друг за другом
    '''

    @classmethod
    def answer_to_user(cls, message_from_user: str, vk_id: int, user_id: int,
                       forward: list, attachment: list, show_keyboard=None):
        check_opened_orders = check_DB.check_opened_orders(user_id)
        cls.attachment_reaction(vk_id, user_id, check_opened_orders, attachment)
        cls.forward_reaction(vk_id, user_id, check_opened_orders, forward)
        send_message = cls.send_message_choice(message_from_user, vk_id, user_id,
                                               forward, attachment, check_opened_orders)
        show_keyboard = keyboard_choice(send_message)
        VKMethods.send_msg('user_id', vk_id, user_id, send_message, show_keyboard)
        if send_message == steps["finish_order"]:
            time.sleep(5)
            VKMethods.send_msg('user_id', vk_id, user_id, bot_grade, keyboard_empty)

    @classmethod
    def attachment_reaction(cls, vk_id: int, user_id: int, check_opened_orders: bool,
                            attachment=None, show_keyboard=None):
        if ((check_opened_orders is False) and (bool(attachment) is True)):
            send_message = answer['attachment_no_message']
            show_keyboard = keyboard_choice(send_message)
            VKMethods.send_msg('user_id', vk_id, user_id, send_message, show_keyboard)
            time.sleep(2)
        elif (check_opened_orders is True and
              VK_attachments.attach_not_files(attachment) is True):
            send_message = answer['incorrect_attachment']
            show_keyboard = keyboard_choice(send_message)
            VKMethods.send_msg('user_id', vk_id, user_id, send_message, show_keyboard)
            time.sleep(2)

    @classmethod
    def forward_reaction(cls, vk_id: int, user_id: int, check_opened_orders: bool,
                         forward=None, show_keyboard=None):
        if ((check_opened_orders is False) and (bool(forward) is True)):
            send_message = answer['forward_alert']
            show_keyboard = keyboard_choice(send_message)
            VKMethods.send_msg('user_id', vk_id, user_id, send_message, show_keyboard)
            time.sleep(2)

    @classmethod
    def send_to_admin(cls, user_id: int, vk_id: int, last_order_id: int):
        order = Order.query.filter(Order.id == last_order_id).first()
        description = json.loads(order.description)

        attachment_received = json.loads(order.attachments)
        attachment = VK_attachments.attach_for_send(attachment_received)
        attachment_links = VK_attachments.attach_links(attachment_received)

        forward_in_order = check_DB.check_forward(last_order_id)
        forward_message = None

        time_finished = dt.strftime(order.finished_at, "%d/%m/%Y %H:%M:%S")
        order_spend_time = str(order.finished_at - order.created_at).split(".")[0]
        dialog_link = f'https://vk.com/gim{group_id}?sel={vk_id}'

        if forward_in_order is True:
            forward_message = '\n\n &#10071; В диалог с чат-ботом отправлены пересланные сообщения.'
        messages = {
            "standard": f'Новый заказ оформлен в {time_finished}. \n\
                          Оформление заказа заняло: {order_spend_time} \n\
                          Ссылка на диалог: {dialog_link} \n\
                          -----------------------\n\
                          Тип заказа: {translate_from_db.get(order.order_type, "Неизвестный тип, что-то сломалось")} \n\
                          Подтип: {translate_from_db.get(order.order_subtype, "Неизвестный тип, что-то сломалось")} \n\
                          Срок: {order.deadline} \n\
                          -----------------------\n\
                          Дата и время: {description.get("time_and_date", "возможно в приложенном файле")} \n\
                          Запрос: {description.get("second_message", "возможно в приложенном файле")} \n\
                          -----------------------\n\
                          Требуемый результат: {description.get("format", "возможно в приложенном файле")} \n\
                          Формат работы: {description.get("time_limit", "возможно в приложенном файле")} \n\
                          Комментарии:  {order.comments} \n\
                          -----------------------\n\
                          Вложения: \n {attachment_links} \n\
                          {forward_message}',
            "cdo": f'Новый заказ оформлен в {time_finished}. \n\
                    Оформление заказа заняло: {order_spend_time} \n\
                    Ссылка на диалог: {dialog_link} \n\
                    -----------------------\n\
                    Тип заказа: {translate_from_db.get(order.order_type, "Неизвестный тип, что-то сломалось")} \n\
                    Подтип: {translate_from_db.get(order.order_subtype, "Неизвестный тип, что-то сломалось")} \n\
                    Срок: {order.deadline} \n\
                    -----------------------\n\
                    Запрос: {description.get("second_message", "возможно в приложенном файле")} \n\
                    -----------------------\n\
                    Требуемые документы: {description.get("format", "возможно в приложенном файле")} \n\
                    Ограничения по времени: {description.get("time_limit", "возможно в приложенном файле")} \n\
                    Дата и время: {description.get("time_and_date", "возможно в приложенном файле")} \n\
                    Комментарии:  {order.comments} \n\
                    -----------------------\n\
                    Вложения: \n {attachment_links} \n\
                    {forward_message}',
            "off_standard": f'Новый заказ оформлен в {time_finished}. \n\
                             Оформление заказа заняло: {order_spend_time} \n\
                             Ссылка на диалог: {dialog_link} \n\
                             -----------------------\n\
                             Тип заказа: {translate_from_db.get(order.order_type, "Неизвестный тип, что-то сломалось")} \n\
                             Подтип: {translate_from_db.get(order.order_subtype, "Неизвестный тип, что-то сломалось")} \n\
                             -----------------------\n\
                             Запрос: {description.get("second_message", "возможно в приложенном файле")} \n\
                             Срок выполнения: {order.deadline} \n\
                             -----------------------\n\
                             Требуемый результат: {description.get("format", "возможно в приложенном файле")} \n\
                             Дата и время: {description.get("time_and_date", "возможно в приложенном файле")} \n\
                             Комментарии:  {order.comments} \n\
                             ----------------------- \n\
                             Вложения: \n {attachment_links} \n\
                             {forward_message}',
            "off_cdo": f'Новый заказ оформлен в {time_finished}. \n\
                         Оформление заказа заняло: {order_spend_time} \n\
                         Ссылка на диалог: {dialog_link} \n\
                         -----------------------\n\
                         Тип заказа: {translate_from_db.get(order.order_type, "Неизвестный тип, что-то сломалось")} \n\
                         Подтип: {translate_from_db.get(order.order_subtype, "Неизвестный тип, что-то сломалось")} \n\
                         -----------------------\n\
                         Запрос: {description.get("second_message", "возможно в приложенном файле")} \n\
                         Срок выполнения: {order.deadline} \n\
                         -----------------------\n\
                         Требуемый результат: {description.get("format", "возможно в приложенном файле")} \n\
                         Ограничение по времени: {description.get("time_limit", "возможно в приложенном файле")} \n\
                         Дата и время: {description.get("time_and_date", "возможно в приложенном файле")} \n\
                         Комментарии:  {order.comments} \n\
                         ----------------------- \n\
                         Вложения: \n {attachment_links} \n\
                         {forward_message}'
        }

        # когда собранная в одном сообщении информация не входит в лимит сообщения ВК, отправляется предложение
        # просмотреть ответы в диалоге с пользователем и ссылка на него

        message = messages.get(order.order_subtype, "Неизвестный тип, что-то сломалось")
        if len(message) > message_limit:
            message = f'Новый заказ оформлен в {time_finished} \n\
                        Ссылка на диалог: {dialog_link} \n\
                        Сообщение слишком длинное для отображения, перейдите в диалог для просмотра ответов.'
        VKMethods.send_msg('user_id', admin_id, user_id, message, keyboard_empty, attachment)
