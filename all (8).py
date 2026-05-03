
from telebot import types
import telebot
import os
from dotenv import load_dotenv

from bot_core import (
    bot, committees, user_states,
    get_user, register_user, create_application,
    get_all_events, add_event, delete_event,
    init_db
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

@bot.message_handler(commands=['start'])
def start(message):
    """Приветствие и регистрация"""
    user = get_user(message.from_user.id)
    if user:
        bot.send_message(message.chat.id, f"✅ Добро пожаловать, {user[2]}!\nВаша роль: {user[3]}")
    else:
        msg = bot.send_message(message.chat.id, "👤 Введите ваше ФИО для регистрации:")
        bot.register_next_step_handler(msg, process_registration)


def process_registration(message):
    """Регистрация пользователя"""
    full_name = message.text
    register_user(message.from_user.id, full_name)
    bot.send_message(message.chat.id, f"✅ Вы успешно зарегистрированы как участник, {full_name}!")


@bot.message_handler(commands=['apply'])
def apply(message):
    """Подача заявки — показывает кнопки с комитетами"""
    user = get_user(message.from_user.id)
    if not user or user[3] != 'participant':
        bot.send_message(message.chat.id, "⚠️ Только участники могут подавать заявки.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in committees:
        markup.add(types.KeyboardButton(c))
    markup.add(types.KeyboardButton("🔙 Назад"))

    msg = bot.send_message(message.chat.id, "Выберите комитет:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: ask_description(m, user[0]))


def ask_description(message, user_id):
    """Обработка выбора комитета"""
    if message.text == "🔙 Назад":
        user_states.pop(message.chat.id, None)
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "❌ Действие отменено.", reply_markup=markup)
        return

    committee = message.text
    if committee not in committees:
        bot.send_message(message.chat.id, "❌ Неверный комитет.")
        return
    
    user_states[message.chat.id] = {'committee': committee, 'user_id': user_id}
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "📝 Введите описание инициативы:", reply_markup=markup)
    bot.register_next_step_handler(msg, save_application)


def save_application(message):
    """Сохранение заявки"""
    state = user_states.pop(message.chat.id, None)
    if not state:
        return
    create_application(state['user_id'], state['committee'], message.text)
    bot.send_message(message.chat.id, "✅ Заявка отправлена!")


@bot.message_handler(commands=['events'])
def list_events(message):
    """Показывает список мероприятий"""
    events = get_all_events()
    if not events:
        bot.send_message(message.chat.id, "📭 Мероприятий пока нет.")
        return
    for event in events:
        eid, title, date, description = event
        bot.send_message(message.chat.id, f"📌 <b>{title}</b>\n📅 {date}\n📝 {description}", parse_mode='HTML')


@bot.message_handler(commands=['addevent'])
def add_event_command(message):
    """Добавление мероприятия (только админ)"""
    user = get_user(message.from_user.id)
    if not user or user[3] != 'admin':
        return
    msg = bot.send_message(message.chat.id, "📝 Введите название мероприятия:")
    bot.register_next_step_handler(msg, get_event_title)


def get_event_title(message):
    user_states[message.chat.id] = {'event_title': message.text}
    msg = bot.send_message(message.chat.id, "📅 Введите дату мероприятия (например, 20.10.2025):")
    bot.register_next_step_handler(msg, get_event_date)


def get_event_date(message):
    state = user_states.get(message.chat.id, {})
    state['event_date'] = message.text
    msg = bot.send_message(message.chat.id, "📝 Введите описание мероприятия:")
    bot.register_next_step_handler(msg, save_event)


def save_event(message):
    """Сохраняет мероприятие в БД"""
    state = user_states.pop(message.chat.id, {})
    title = state.get('event_title')
    date = state.get('event_date')
    description = message.text
    if title and date:
        add_event(title, date, description)
        bot.send_message(message.chat.id, "✅ Мероприятие добавлено.")
    else:
        bot.send_message(message.chat.id, "⚠️ Ошибка при добавлении мероприятия.")


@bot.message_handler(commands=['cancelapp'])
def cancel_last_application(message):
    """Удаляет последнюю заявку"""
    from bot_core import cancel_last_application as core_cancel
    core_cancel(message, bot)


@bot.message_handler(commands=['help'])
def help_command(message):
    """Справка по командам"""
    help_text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "👋 /start — Начало работы и регистрация\n"
        "📋 /apply — Подать заявку в один из комитетов\n"
        "🔙 Назад — Отменить подачу заявки на этапе выбора комитета или описания\n"
        "🗑 /cancelapp — Удалить последнюю отправленную заявку\n"
        "📆 /events — Посмотреть план мероприятий\n"
        "➕ /addevent — (только для админов) Добавить мероприятие\n"
        "ℹ️ /help — Показать это сообщение\n"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')



if __name__ == '__main__':
    init_db()
    print("🤖 Бот запущен (интерфейсная часть)")
    bot.polling(non_stop=True)