from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base, engine

'''
Схема БД состоит из трёх сущностей: пользователя, заказа и сообщения.
Таблица с сообщениями используется только для хранения истории диалогов, к ней применяются лишь запросы типа INSERT.
Сообщения хранятся закодированными и необходимы только для аналитики диалогов.
Для упрощения аналитики используются коды сообщений, которые определены для команд бота и ответов на них.
Остальные сообщения кодируются как "other".

Таблицы с заказами и пользователями используются при обработке новых входящих сообщений,
чтобы определить ветку диалога и выбрать ответ для пользователя.

Связь пользователей и заказов - один ко многим, пользователей и сообщений - один ко многим.
Во всех таблицах записывается параметр group_id, который соответствует id группы, к которой относится событие
(сообщение пользователя, оформление заказа), поскольку предполагается, что бот как веб-приложение может быть привязан к
нескольким группам, связанным одной БД.
'''


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    vk_id = Column(Integer)
    group_id = Column(String)
    name = Column(String)
    bot_off = Column(Boolean, default=False)  # флаг, указывающий на статус бота: включён / выключен

    def __init__(self, vk_id, group_id, name):
        self.vk_id = vk_id
        self.group_id = group_id
        self.name = name

    def __repr__(self):
        return f'Vk_id:{self.vk_id}; name:{self.name}'


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String)  # статус заказа (открыт, отменён, завершён)
    order_type = Column(String)  # тип заказа или вид услуги
    order_subtype = Column(String)  # подтип заказа (конкретная услуга в выбранном типе)
    user_id = Column(Integer, ForeignKey(User.id))
    group_id = Column(String)
    description = Column(JSON)  # содержит ответы на типовые вопросы к клиенту по выбранной услуге
    attachments = Column(JSON)  # содержит все прикреплённые файлы к сообщениям клиента
    forward = Column(Boolean, default=False)  # флаг, указывающий на то, есть ли в сообщениях от клиента пересланные
    deadline = Column(String)  # срок выполнения либо желаемая дата оказания услуги
    comments = Column(String)  # комментарии к заказу
    sended = Column(Boolean, default=False)  # флаг состояния, указывающий на то, что все необходимые поля заполнены корректно
    finished_at = Column(DateTime(timezone=True), server_default=func.now())  # момент завершения оформления заказа

    user = relationship(User, backref="orders")

    def __init__(self, status, order_type, order_subtype, user_id, group_id):
        self.status = status
        self.order_type = order_type
        self.order_subtype = order_subtype
        self.user_id = user_id
        self.group_id = group_id


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey(User.id))
    group_id = Column(String)
    msg_type = Column(String)  # тип сообщения - входящее или исходящее
    msg_code = Column(String)

    user = relationship(User, backref="messages")

    def __init__(self, user_id, group_id, msg_type, msg_code):
        self.user_id = user_id
        self.group_id = group_id
        self.msg_type = msg_type
        self.msg_code = msg_code


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
