# -
#import telebot 
#from telebot import types

'''bot = telebot.TeleBot('8260494634:AAGy8iqWQsVeMzl-oXviPsYrNB6yo3ijthk')


@bot.message_handler(commands=['start'])
def get_photo(message):
    #markup = types.InlineKeyboardMarkup()
    markup = types.InlineKeyboardMarkup()

    bot.delete_message(message.chat.id, message.message_id)

    student_btn = types.InlineKeyboardButton('Ученик', callback_data='student')
    admin_btn = types.InlineKeyboardButton('Администрация', callback_data='admin')
    markup.row(student_btn, admin_btn)

    bot.send_message(message.chat.id, 'Выбирете свою роль:', reply_markup=markup)
    #btn = types.InlineKeyboardButton('удалить фото ')
    #markup.add(types.InlineKeyboardButton('перейти на сайт', url='https://wildberries.ru/basket?shareId=ths5ollnz6'))
    markup.add()
   # bot.send_message(message, 'красивое фото ', reply_markup=markup)

bot.polling(none_stop=True)'''



import telebot
from telebot import types
import sqlite3


TOKEN = '8260494634:AAGy8iqWQsVeMzl-oXviPsYrNB6yo3ijthk'
bot = telebot.TeleBot(TOKEN)

committees = ['Творческий', 'Спортивный', 'СМИ', 'Технический', 'Киберспортивный', 'Социальный']
user_states = {}


def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            role TEXT DEFAULT 'participant'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            committee TEXT,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            description TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()


def register_user(telegram_id, full_name):
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, full_name, role) VALUES (?, ?, ?)',
                     (telegram_id, full_name, 'participant'))

def get_user(telegram_id):
    with sqlite3.connect('bot.db') as conn:
        cursor = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()

def create_application(user_id, committee, description):
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT INTO applications (user_id, committee, description) VALUES (?, ?, ?)',
                     (user_id, committee, description))

def add_event(title, date, description):
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT INTO events (title, date, description) VALUES (?, ?, ?)', (title, date, description))

def get_all_events():
    with sqlite3.connect('bot.db') as conn:
        cursor = conn.execute('SELECT * FROM events ORDER BY date')
        return cursor.fetchall()

def delete_event(event_id):
    with sqlite3.connect('bot.db') as conn:
        conn.execute('DELETE FROM events WHERE id = ?', (event_id,))


@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.from_user.id)
    if user:
        bot.send_message(message.chat.id, f"✅ Добро пожаловать, {user[2]}!\nВаша роль: {user[3]}")
    else:
        msg = bot.send_message(message.chat.id, "👤 Введите ваше ФИО для регистрации:")
        bot.register_next_step_handler(msg, process_registration)

def process_registration(message):
    full_name = message.text
    register_user(message.from_user.id, full_name)
    bot.send_message(message.chat.id, f"✅ Вы успешно зарегистрированы как участник, {full_name}!")

@bot.message_handler(commands=['apply'])
def apply(message):
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
    if message.text == "🔙 Назад":
        user_states.pop(message.chat.id, None)
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "❌ Действие отменено.", reply_markup=markup)
        return

    committee = message.text
    if committee not in committees:
        bot.send_message(message.chat.id, "❌ Неверный комитет.")
        return

Masha Karzhavina, [10.10.2025 19:16]
user_states[message.chat.id] = {'committee': committee, 'user_id': user_id}
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "📝 Введите описание инициативы:", reply_markup=markup)
    bot.register_next_step_handler(msg, save_application)

def save_application(message):
    state = user_states.pop(message.chat.id, None)
    if not state:
        return
    create_application(state['user_id'], state['committee'], message.text)
    bot.send_message(message.chat.id, "✅ Заявка отправлена!")

@bot.message_handler(commands=['events'])
def list_events(message):
    events = get_all_events()
    if not events:
        bot.send_message(message.chat.id, "📭 Мероприятий пока нет.")
        return
    for event in events:
        eid, title, date, description = event
        bot.send_message(message.chat.id, f"📌 <b>{title}</b>\n📅 {date}\n📝 {description}", parse_mode='HTML')

@bot.message_handler(commands=['addevent'])
def add_event_command(message):
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
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "⚠️ Вы не зарегистрированы.")
        return

    with sqlite3.connect('bot.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM applications
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        ''', (user[0],))
        result = cursor.fetchone()

        if result:
            app_id = result[0]
            cursor.execute('DELETE FROM applications WHERE id = ?', (app_id,))
            conn.commit()
            bot.send_message(message.chat.id, "✅ Ваша последняя заявка удалена.")
        else:
            bot.send_message(message.chat.id, "📭 У вас нет активных заявок.")


@bot.message_handler(commands=['help'])
def help_command(message):
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


bot.polling(non_stop=True)



