from datetime import datetime
import json
from db import db_session
from db_models import User, Order, Message
from messages import bot_command_on, bot_off_command
from settings import group_id


# функция обработки текстов для получения корректных команд в случае, если они введены с ошибкой
def str_transform(string: str):
    return string.lower().strip().capitalize()


'''
В этом файле собраны функции, с помощью которых происходит взаимодействие бота с БД.
Для удобства использования функции объединены в классы по признаку цели запроса:
* check_DB - проверка выполнения заданных условий;
* get_DB - получение информации;
* Upsert_DB - добавление и обновление информации;
* Bot_status - работа с состояниями бота ("включён" / "выключен")
* Messages_DB - добавление сообщений в БД;
* DB_queries - пользовательские запросы к БД.
'''


class check_DB():

    '''
    В данном классе собраны функции, которые проверяют: "включен" ли бот для данного пользователя, является ли пользователь новым,
    есть ли у него открытые заказы, корректно ли заполнены поля анкеты заказа, содержит ли сообщение пользователя перепост другого сообщения.
    В названии функции отражено её назначение.
    '''

    @staticmethod
    def check_old_user(vk_id: int):
        return bool(User.query.filter(
            User.vk_id == vk_id,
            User.group_id == group_id).count())

    @staticmethod
    def check_opened_orders(user_id: int):
        try:
            opened_orders = Order.query.filter(
                Order.user_id == user_id,
                Order.group_id == group_id,
                Order.status == 'opened').count()
            return bool(opened_orders)
        except AttributeError:
            return False

    @staticmethod
    def check_empty_description(opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return bool(order.description)

    @staticmethod
    def check_order_deadline(opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return bool(order.deadline)

    @staticmethod
    def check_order_comments(opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return bool(order.comments)

    @staticmethod
    def check_correct_order(last_order_id: int):
        if last_order_id is not None:
            order = Order.query.filter(
                Order.id == last_order_id,
                Order.group_id == group_id).first()
            correct_order = ((order.deadline is not None) and
                             (order.comments is not None) and
                             (order.description is not None) and
                             (order.sended is False) and order.status == "finished")
            if correct_order:
                return True

    @staticmethod
    def check_bot_off(user_id: int):
        try:
            user = User.query.filter(
                User.id == user_id,
                User.group_id == group_id).first()
            return user.bot_off
        except AttributeError:
            return False

    @staticmethod
    def check_forward(last_order_id: int):
        if last_order_id is not None:
            order = Order.query.filter(
                Order.id == last_order_id,
                Order.group_id == group_id).first()
            if order.forward is True:
                return True


class get_DB():

    '''
    В этом классе объединены функции для получения данных из БД, которые необходимы для обработки сообщений
    от пользователей и направления их на ту или иную ветку диалога.
    Используются следующие функции получения данных: получение id пользователя, id последнего открытого заказа,
    подтипа, описания и вложений к последнему открытому заказу, а также id последнего заказа, который был создан пользователем.
    В названии функции отражено её назначение.
    '''

    @staticmethod
    def get_user_id(vk_id: int):
        try:
            user = User.query.filter(
                User.vk_id == vk_id,
                User.group_id == group_id).first()
            return user.id
        except AttributeError:
            pass

    @classmethod
    def get_opened_order(cls, user_id: int):
        try:
            order = Order.query.filter(
                Order.user_id == user_id,
                Order.group_id == group_id,
                Order.status == 'opened').first()
            return order.id
        except AttributeError:
            pass

    @classmethod
    def get_order_subtype(cls, opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return order.order_subtype

    @classmethod
    def get_order_description(cls, opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return order.description

    @classmethod
    def get_order_attachment(cls, opened_order_id: int):
        if opened_order_id is not None:
            order = Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).first()
            return order.attachments

    @classmethod
    def get_last_order(cls, user_id: int):
        if user_id is not None:
            order = Order.query.filter(
                Order.user_id == user_id,
                Order.group_id == group_id) \
                .order_by(Order.created_at.desc()).first()
            return order.id


class Upsert_DB():

    '''
    В этом классе объединены функции добавления и изменения данных в БД.
    Они включают: добавление нового пользователя в БД, добавление нового заказа (отдельная функция для каждого типа),
    добавление описания к заказу, сроков, вложений и комментариев. Также изменение статуса заказа на завершённый
    либо отменённый. И установка меток в заказе о содержании перепостов сообщений и проверке корректности заполнения всех полей.
    В названии функции отражено её назначение.
    '''

    @staticmethod
    def add_user(vk_id: int, name: str):
        user = User(vk_id=vk_id, group_id=group_id, name=name)
        if check_DB.check_old_user(vk_id) is False:
            db_session.add(user)
            db_session.commit()

    @staticmethod
    def add_order_standard_online(user_id: int):
        if user_id is not None:
            order = Order(status="opened", order_type="online",
                          order_subtype="standard",
                          user_id=user_id, group_id=group_id)
            db_session.add(order)
            db_session.commit()

    @staticmethod
    def add_order_cdo_online(user_id: int):
        if user_id is not None:
            order = Order(status="opened", order_type="online",
                          order_subtype="cdo",
                          user_id=user_id, group_id=group_id)
            db_session.add(order)
            db_session.commit()

    @staticmethod
    def add_order_cdo_offline(user_id: int):
        if user_id is not None:
            order = Order(status="opened", order_type="offline",
                          order_subtype="off_cdo",
                          user_id=user_id, group_id=group_id)
            db_session.add(order)
            db_session.commit()

    @staticmethod
    def add_order_standard_offline(user_id: int):
        if user_id is not None:
            order = Order(status="opened", order_type="offline",
                          order_subtype="off_standard",
                          user_id=user_id, group_id=group_id)
            db_session.add(order)
            db_session.commit()

    @staticmethod
    def add_order_description(opened_order_id: int, description: json):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.description: description}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def add_order_attachment(opened_order_id: int, attachment: list):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.attachments: attachment}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def add_order_deadline(opened_order_id: int, deadline: str):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.deadline: deadline}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def add_order_comments(opened_order_id: int, comments: str):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.comments: comments}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def cancel_order(opened_order_id: int):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.status: "cancelled"}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def finish_order(opened_order_id: int):
        if opened_order_id is not None:
            Order.query.filter(
                Order.id == opened_order_id,
                Order.group_id == group_id).update({
                    Order.status: "finished"}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def sended_mark_on(last_order_id: int):
        if last_order_id is not None:
            Order.query.filter(
                Order.id == last_order_id,
                Order.group_id == group_id) \
                .update({
                    Order.sended: True,
                    Order.finished_at: datetime.now()},
                    synchronize_session=False)
            db_session.commit()

    @staticmethod
    def mark_forward(last_order_id: int):
        if last_order_id is not None:
            Order.query.filter(
                Order.id == last_order_id,
                Order.group_id == group_id).update({
                    Order.forward: True}, synchronize_session=False)
            db_session.commit()


class Bot_status():

    '''
    Бот может быть выключен несколькими способами: автоматически при завершении оформления заказа,
    по команде администратора, по команде от пользователя (при сценарии выбора обращения администратору).
    Для каждого способа создана отдельная функция. Также в этом классе находится функция включения бота.
    В названии функции отражено её назначение.
    '''

    @staticmethod
    def turn_off(user_id: int, last_order_id: int):
        if (user_id is not None) and (last_order_id is not None):
            order = Order.query.filter(
                Order.id == last_order_id,
                Order.group_id == group_id).first()
            if order.status == 'finished' and order.sended is True:
                User.query.filter(
                    User.id == user_id,
                    User.group_id == group_id) \
                    .update({User.bot_off: True}, synchronize_session=False)
                db_session.commit()

    @staticmethod
    def turn_off_call_admin(user_id: int):
        if user_id is not None:
            User.query.filter(
                User.id == user_id,
                User.group_id == group_id) \
                .update({User.bot_off: True}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def turn_off_by_command(message_from_user: str, user_id: int):
        if (user_id is not None) and (str_transform(message_from_user) == bot_off_command):
            User.query.filter(
                User.id == user_id,
                User.group_id == group_id) \
                .update({User.bot_off: True}, synchronize_session=False)
            db_session.commit()

    @staticmethod
    def turn_on(message_from_user: str, user_id: int):
        if (user_id is not None) and (str_transform(message_from_user) in bot_command_on) and \
                (check_DB.check_bot_off(user_id) is True):
            User.query.filter(
                User.id == user_id,
                User.group_id == group_id) \
                .update({User.bot_off: False}, synchronize_session=False)
            db_session.commit()


class Messages_DB():

    # в этом классе объединены функции добавления сообщений в БД
    # отдельно функция для входящего и исходящего сообщения

    @staticmethod
    def add_incoming_msg(user_id: int, message_code: str):
        if user_id is not None:
            message = Message(user_id=user_id, group_id=group_id,
                              msg_type="incoming", msg_code=message_code)
            db_session.add(message)
            db_session.commit()

    @staticmethod
    def add_outcoming_msg(user_id: int, message_code: str):
        if user_id is not None:
            message = Message(user_id=user_id, group_id=group_id,
                              msg_type="outcoming", msg_code=message_code)
            db_session.add(message)
            db_session.commit()


class DB_queries():

    '''
    В данном классе содержатся функции, исполнение которых формирует специфичный запрос к БД.
    На данный момент таким запросом является лишь запрос информации о пользователях, у которых отключен чат-бот.
    Функция выполняется при отправке команды администратора в чат сообщества и сообщество ответом выдаёт список
    таких пользователей в настроенном формате.
    '''

    @staticmethod
    def get_users_bot_off():
        try:
            user = User.query.filter(User.group_id == group_id) \
                             .filter(User.bot_off is True).all()
            users_list = list()
            users_list.append('Пользователи, у которых отключён чат-бот:')
            for user_i in user:
                s_user = str(user_i)
                username = s_user[s_user.index(';') + 7:]
                userid = s_user[6:s_user.index(';')]
                users_list.append(f'\n\n {username}, \
                    диалог: https://vk.com/gim{group_id}?sel={userid}')
            return users_list
        except AttributeError:
            return 'Возникла ошибка при выполнении команды.'
