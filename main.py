import requests
import time
import json
from datetime import datetime, timedelta

TOKEN = "8378183612:AAH9ieJczLQ4rgbSvc38PGn8ML39S2DvbGU"
ADMIN_ID = 8378183612
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

users = {}
shared_codes = [("BDTDW4", "Евгений Клочков", "@Evgeniy_Klochkov")]  # пример
daily_limit = 10
maintenance_mode = False

def api(method, payload):
    """Удобная обёртка для POST-запросов к Telegram API"""
    url = f"{BASE_URL}/{method}"
    return requests.post(url, json=payload).json()

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        # Telegram ожидает reply_markup как JSON-строку
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    api("sendMessage", payload)

def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = False
    api("answerCallbackQuery", payload)

def get_updates(offset=None, timeout=30):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    return requests.get(f"{BASE_URL}/getUpdates", params=params).json()

def build_inline(rows):
    # rows: list of lists of (text, callback_data)
    kb = {"inline_keyboard": [[{"text": t, "callback_data": d} for (t, d) in row] for row in rows]}
    return kb

def build_keyboard(rows):
    kb = {"keyboard": [[{"text": t} for t in row] for row in rows], "resize_keyboard": True}
    return kb

def get_user(uid):
    if uid not in users:
        users[uid] = {"codes_received": 0, "shared": 0, "last_reset": datetime.now(), "pending_code": None, "waiting_for_code": False}
    user = users[uid]
    if datetime.now() - user["last_reset"] > timedelta(days=1):
        user["codes_received"] = 0
        user["last_reset"] = datetime.now()
    return user

def handle_message(msg):
    global maintenance_mode
    chat = msg["chat"]
    chat_id = chat["id"]
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    user = get_user(chat_id)

    # технические работы
    if maintenance_mode and chat_id != ADMIN_ID:
        send_message(chat_id, "🚧 Бот временно недоступен — идут тех. работы.")
        return

    if text == "/start":
        send_message(chat_id, "👋 Привет! Выбери действие:", reply_markup=build_keyboard([["💎 Получить код"], ["🔁 Поделиться кодом"], ["🏆 Топ пользователей"]]))
        return

    if text == "💎 Получить код":
        if user["codes_received"] >= daily_limit:
            send_message(chat_id, "⚠️ Лимит 10 кодов в день. Попробуй завтра.")
            return
        if not shared_codes:
            send_message(chat_id, "⏳ Пока нет доступных кодов — попроси кого-то поделиться.")
            return

        # выдаём первый код из очереди
        code_data = shared_codes.pop(0)
        user["pending_code"] = code_data
        user["codes_received"] += 1

        send_message(
            chat_id,
            "Сейчас ты можешь получить код, потому что кто-то другой им поделился с тобой.\n\n"
            "После регистрации, пожалуйста, потом поделись полученным кодом — так ты поможешь другому человеку. Поделишься?🥹",
            reply_markup=build_inline([[("Да", "yes_share"), ("Нет", "no_share")]])
        )
        return

    if text == "🔁 Поделиться кодом":
        user["waiting_for_code"] = True
        send_message(chat_id, "📨 Введи код, которым хочешь поделиться (только сам код):")
        return

    if text == "🏆 Топ пользователей":
        top = sorted(users.items(), key=lambda x: x[1]["shared"], reverse=True)[:20]
        if not top:
            send_message(chat_id, "Пока нет данных по топу.")
            return
        msg = "🏆 Топ пользователей по числу поделившихся кодов:\n\n"
        for i, (uid, data) in enumerate(top, start=1):
            msg += f"{i}. <a href='tg://user?id={uid}'>Пользователь</a> — {data['shared']} кодов\n"
        send_message(chat_id, msg)
        return

    if user.get("waiting_for_code"):
        code = text.strip().upper()
        shared_codes.append((code, from_user.get("first_name", "User"), f"@{from_user.get('username','no')}"))
        user["waiting_for_code"] = False
        user["shared"] += 1
        send_message(chat_id, f"✅ Спасибо! Код {code} добавлен и доступен другим.")
        return

    # Кнопки текстовые после выдачи кода (если используются пользователем через клавиатуру)
    if text == "✅ Спасибо, работает!":
        user["pending_code"] = None
        send_message(chat_id, "🎉 Отлично! Спасибо за подтверждение.")
        return

    if text == "❌ Код недействителен":
        code_data = user.get("pending_code")
        if code_data:
            # удаляем из очереди (если где-то ещё остался) и очищаем pending
            shared_codes[:] = [c for c in shared_codes if c != code_data]
            user["pending_code"] = None
            send_message(chat_id, "🚫 Код помечен как недействительный и удалён.")
        else:
            send_message(chat_id, "⚠️ Нет активного кода для пометки.")
        return

    # Админ команда
    if chat_id == ADMIN_ID and text == "/admin":
        send_message(chat_id, "👑 Админ-панель", reply_markup=build_keyboard([
            ["👥 Пользователи", "📦 Очередь кодов"],
            ["🧹 Вайп данных", "🚧 Тех. работы"],
            ["⬅️ Назад"]
        ]))
        return

    if chat_id == ADMIN_ID and text == "👥 Пользователи":
        msg = "📋 Пользователи:\n\n"
        for uid, d in users.items():
            msg += f"• <a href='tg://user?id={uid}'>User {uid}</a> — shared: {d['shared']}, got today: {d['codes_received']}\n"
        send_message(chat_id, msg or "Нет пользователей.")
        return

    if chat_id == ADMIN_ID and text == "📦 Очередь кодов":
        msg = "📦 Очередь кодов:\n\n" + "\n".join([f"{i+1}. {c[0]} — {c[1]} ({c[2]})" for i, c in enumerate(shared_codes)]) if shared_codes else "Очередь пуста."
        send_message(chat_id, msg)
        return

    if chat_id == ADMIN_ID and text == "🧹 Вайп данных":
        shared_codes.clear()
        users.clear()
        send_message(chat_id, "⚠️ Все данные очищены.")
        return

    if chat_id == ADMIN_ID and text == "🚧 Тех. работы":
        maintenance_mode = not maintenance_mode
        send_message(chat_id, f"🚨 Тех. работы {'включены' if maintenance_mode else 'выключены'}.")
        return

    # Если ни одно условие не сработало — короткий ответ
    # (оставляем минимальный fallback, чтобы пользователь видел реакцию)
    # send_message(chat_id, "Не понял команду. Выбери кнопку меню.")

def handle_callback(cb):
    """
    cb — callback_query object из Telegram.
    Важно вызвать answerCallbackQuery, иначе у пользователя будет крутилка.
    """
    cid = cb["id"]
    data = cb["data"]
    from_user = cb["from"]
    chat_id = cb["message"]["chat"]["id"]
    user = get_user(chat_id)

    # Подтверждаем callback у клиента
    answer_callback(cid)

    if data == "yes_share":
        code_data = user.get("pending_code")
        if not code_data:
            send_message(chat_id, "⚠️ Ошибка: код не найден.")
            return

        code, author_name, author_username = code_data
        # отправляем сообщение с inline-кнопками для результата
        text = (f"Твой код: <b>{code}</b>\n\n"
                f"👤 Кодом поделился: {author_name} ({author_username})\n\n"
                "📱 Инструкция по установке:\n1. Смени регион App Store на США: https://t-j.ru/apple-region/\n"
                "2. Скачай приложение: https://apps.apple.com/us/app/sora-by-openai/id6744034028\n\n"
                "Если всё ок — нажми кнопку ниже, если нет — тоже нажми.")
        ik = {
            "inline_keyboard": [
                [{"text": "✅ Спасибо, работает!", "callback_data": "ok"}, {"text": "❌ Код недействителен", "callback_data": "bad"}]
            ]
        }
        send_message(chat_id, text, reply_markup=ik)
        return

    if data == "no_share":
        send_message(chat_id, "😔 Хорошо — в следующий раз поделишься!")
        user["pending_code"] = None
        return

    if data == "ok":
        user["pending_code"] = None
        user["shared"] += 0  # можно логировать успешное получение
        send_message(chat_id, "🎉 Спасибо за подтверждение — рад что помогло!")
        return

    if data == "bad":
        code_data = user.get("pending_code")
        if code_data:
            # удаляем код из очереди (если он где-то остался)
            shared_codes[:] = [c for c in shared_codes if c != code_data]
            user["pending_code"] = None
            send_message(chat_id, "🚫 Код помечен как недействительный и удалён.")
        else:
            send_message(chat_id, "⚠️ Нет активного кода для удаления.")
        return

def main():
    offset = None
    print("Бот запущен...")
    while True:
        resp = get_updates(offset, timeout=30)
        if not resp.get("ok"):
            time.sleep(1)
            continue
        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1
            if "message" in upd:
                handle_message(upd["message"])
            elif "callback_query" in upd:
                handle_callback(upd["callback_query"])
        time.sleep(0.5)

if __name__ == "__main__":
    main()
