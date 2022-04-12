from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from messages import steps, keyboard_answer, error_messages
from messages import keyboard_command as button
from messages import conditions_answer as message
from messages import order_command as order


# функция упрощённого выбора цвета кнопки через обращение к VK API клавиатуры
def colors(col):
    color = {
        "green": VkKeyboardColor.POSITIVE,
        "red": VkKeyboardColor.NEGATIVE,
        "white": VkKeyboardColor.SECONDARY,
        "blue": VkKeyboardColor.PRIMARY
    }
    col_func = color.get(col)
    return col_func


'''
Каждая функция в данном файле отвечает за формирование клавиатуры, которая будет
отправлена вместе с ответным сообщением пользователю.
'''


def keyboard_start():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button('Начать', color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_menu():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_begin():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["order"], color=colors("red"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["consulting"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["about"], color=colors("blue"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["admin_menu_1"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_order():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["offline"], color=colors("blue"))
    create_keyboard.add_button(button["online"], color=colors("red"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["consulting"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("white"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["admin_menu_1"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_about():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["prices"], color=colors("blue"))
    create_keyboard.add_button(button["conditions"], color=colors("red"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["refs"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_about_back():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["about"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_cancel():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["cancel"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_empty():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard = create_keyboard.get_empty_keyboard()
    return create_keyboard


def keyboard_online():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["emergency"], color=colors("red"))
    create_keyboard.add_button(button["later"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_offline():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(order["off_standard"], color=colors("red"))
    create_keyboard.add_button(order["off_cdo"], color=colors("green"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_online_choose():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(order["standard"], color=colors("green"))
    create_keyboard.add_button(order["cdo"], color=colors("blue"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["menu"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_admin_connect():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard.add_line()
    create_keyboard.add_button(button["admin_menu_2"], color=colors("white"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


def keyboard_consulting():
    create_keyboard = VkKeyboard(one_time=True)
    create_keyboard.add_button(button["menu"], color=colors("blue"))
    create_keyboard = create_keyboard.get_keyboard()
    return create_keyboard


'''
В keyboard_map приведено соответствие отправляемых пользователю сообщений и клавиатур, которые должны быть
к этим сообщениям прикреплены. Функция keyboard_choice возвращает выбранную клавиатуру.
'''


keyboard_map = {
    keyboard_answer['cancel']: keyboard_menu,
    keyboard_answer['beginning']: keyboard_begin,
    keyboard_answer['about']: keyboard_about,
    message['1st_message_new_client']: keyboard_begin,
    message['1st_message_old_client']: keyboard_begin,
    keyboard_answer['prices']: keyboard_about_back,
    keyboard_answer['refs']: keyboard_about_back,
    keyboard_answer['conditions']: keyboard_about_back,
    keyboard_answer['online']: keyboard_online,
    keyboard_answer['later']: keyboard_online_choose,
    keyboard_answer['cdo']: keyboard_cancel,
    keyboard_answer['standard']: keyboard_cancel,
    keyboard_answer['off_standard']: keyboard_cancel,
    keyboard_answer['off_cdo']: keyboard_cancel,
    keyboard_answer['offline']: keyboard_offline,
    keyboard_answer['admin_menu_1']: keyboard_admin_connect,
    keyboard_answer['consulting']: keyboard_consulting,
    keyboard_answer['emergency']: keyboard_menu,
    keyboard_answer['order']: keyboard_order,
    error_messages['unknown_command']: keyboard_menu,
    error_messages['incorrect_command']: keyboard_cancel,
    error_messages["attachment_no_message"]: keyboard_menu,
    error_messages["forward_alert"]: keyboard_menu,
    error_messages['incorrect_attachment']: keyboard_cancel
}

'''
В функции steps_answers предварительно все сообщения на шагах оформления заказа собраны в один список,
чтобы на этих шагах выводить одну и ту же клавиатуру.
В остальных случаях выводится клавиатура в соответствии с keyboard_map.
'''

steps_answers = []
for i in list(steps)[:-2]:
    for j in steps.get(i).values():
        steps_answers.append(j)


def keyboard_choice(send_message):
    if send_message in steps_answers:
        return keyboard_cancel
    else:
        return keyboard_map.get(send_message, keyboard_empty)
