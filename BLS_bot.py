# bot_core.py - отвечает за внутреннюю логику: ядро бота, базу данных, состояния (FSM)

import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

# Загружаем токен
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Создаём экземпляр бота (ядро)
bot = telebot.TeleBot(TOKEN)

# Константы и хранилище состояний
committees = ['Творческий', 'Спортивный', 'СМИ', 'Технический', 'Киберспортивный', 'Социальный']
user_states = {}  # FSM: хранит временные данные пользователей


# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========

def init_db():
    """Инициализация БД: создание таблиц"""
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


def register_user(telegram_id, full_name):
    """Регистрирует нового пользователя с ролью 'participant'"""
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, full_name, role) VALUES (?, ?, ?)',
                     (telegram_id, full_name, 'participant'))


def get_user(telegram_id):
    """Возвращает данные пользователя по telegram_id"""
    with sqlite3.connect('bot.db') as conn:
        cursor = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()


def create_application(user_id, committee, description):
    """Сохраняет заявку в БД"""
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT INTO applications (user_id, committee, description) VALUES (?, ?, ?)',
                     (user_id, committee, description))


def add_event(title, date, description):
    """Добавляет мероприятие в БД"""
    with sqlite3.connect('bot.db') as conn:
        conn.execute('INSERT INTO events (title, date, description) VALUES (?, ?, ?)', (title, date, description))


def get_all_events():
    """Возвращает все мероприятия из БД, отсортированные по дате"""
    with sqlite3.connect('bot.db') as conn:
        cursor = conn.execute('SELECT * FROM events ORDER BY date')
        return cursor.fetchall()


def delete_event(event_id):
    """Удаляет мероприятие по ID"""
    with sqlite3.connect('bot.db') as conn:
        conn.execute('DELETE FROM events WHERE id = ?', (event_id,))


# ========== СЛОЖНАЯ ЛОГИКА (FSM, ВАЛИДАЦИЯ) ==========

def cancel_last_application(message, bot_instance):
    """Логика удаления последней заявки (вызывается из UI)"""
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
