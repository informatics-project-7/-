1. Импорты, загрузка токена и создание ядра бота
Я подключила все нужные библиотеки: telebot для бота, sqlite3 для базы данных, os и dotenv для токена. Потом загрузила токен из скрытого файла и создала главного бота, через которого будут приходить и уходить все сообщения.

import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
2. Список комитетов и хранилище состояний
Я создала список всех комитетов, чтобы не перечислять их каждый раз заново. А ещё сделала пустой словарь user_states — в нём будут временно лежать данные, пока человек проходит длинный диалог (выбирает комитет, потом пишет описание и так далее).

committees = ['Творческий', 'Спортивный', 'СМИ', 'Технический', 'Киберспортивный', 'Социальный']
user_states = {}
3. Настройка базы данных — создание таблиц
Функция init_db() открывает базу данных bot.db и создаёт в ней три таблицы, если их ещё нет: таблицу пользователей (с именем, айди в телеграме и ролью), таблицу заявок (кто в какой комитет что написал) и таблицу мероприятий (название, дата, описание). Это как чистый лист, с которого всё начинается.

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
4. Функции для работы с пользователями и заявками
Я написала несколько маленьких помощников:
register_user — запоминает нового человека в базе с ролью «участник».
get_user — ищет человека по его телеграм-айди.
create_application — сохраняет заявку в таблицу заявок.
Каждая функция подключается к базе, делает своё дело и закрывает соединение. Это как простые команды для работы с базой, чтобы каждый раз не писать одно и то же.

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
5. Функции для мероприятий
Тут три функции:
add_event — добавляет новое мероприятие.
get_all_events — забирает все мероприятия из базы и сортирует по дате.
delete_event — удаляет мероприятие по его номеру.
Эти функции использует админ, когда хочет добавить или убрать мероприятие.

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
6. Сложная логика — удаление последней заявки
Это не просто функция, а целая история. Она сначала находит человека в базе, потом ищет его самую последнюю заявку (сортируем по убыванию и берём первую), и если находит — удаляет. А если нет — вежливо говорит, что заявок нет. Эту функцию я не положила в первый файл (UI), потому что там и так много текста, а здесь ей самое место — рядом с базой данных.

def cancel_last_application(message, bot_instance):
    user = get_user(message.from_user.id)
    if not user:
        bot_instance.send_message(message.chat.id, "⚠️ Вы не зарегистрированы.")
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
            bot_instance.send_message(message.chat.id, "✅ Ваша последняя заявка удалена.")
        else:
            bot_instance.send_message(message.chat.id, "📭 У вас нет активных заявок.")
