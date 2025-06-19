import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import json
import os
from datetime import datetime

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")
DELAY_MINUTES = int(os.getenv("DELAY_MINUTES", 5))
QUEUE_FILE = "queue.json"

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

if not os.path.exists(QUEUE_FILE):
    with open(QUEUE_FILE, "w") as f:
        json.dump({"messages": [], "targets": []}, f)

def load_queue():
    with open(QUEUE_FILE) as f:
        return json.load(f)

def save_queue(data):
    with open(QUEUE_FILE, "w") as f:
        json.dump(data, f)

@client.on(events.NewMessage(incoming=True, pattern=r"\.add"))
async def add_handler(event):
    if event.is_private:
        queue = load_queue()
        reply = await event.get_reply_message()
        if reply:
            queue["messages"].append(reply.id)
            save_queue(queue)
            await event.reply("✅ Добавлено.")
        else:
            await event.reply("❌ Ответь на сообщение командой .add")

@client.on(events.NewMessage(incoming=True, pattern=r"\.delete"))
async def del_handler(event):
    if event.is_private:
        queue = load_queue()
        if queue["messages"]:
            removed = queue["messages"].pop()
            save_queue(queue)
            await event.reply(f"❌ Удалено сообщение ID: {removed}")
        else:
            await event.reply("📭 Очередь пуста.")

@client.on(events.NewMessage(incoming=True, pattern=r"\.help"))
async def help_handler(event):
    if event.is_private:
        await event.reply(
            "📌 Команды:\n"
            ".add — добавить сообщение в очередь (ответом)\n"
            ".delete — удалить последнее сообщение\n"
            ".target — добавить чат в цели (ответом)\n"
            ".help — показать справку"
        )

@client.on(events.NewMessage(incoming=True, pattern=r"\.target"))
async def target_handler(event):
    if event.is_private:
        reply = await event.get_reply_message()
        if reply and reply.chat_id:
            queue = load_queue()
            if reply.chat_id not in queue["targets"]:
                queue["targets"].append(reply.chat_id)
                save_queue(queue)
                await event.reply("🎯 Цель добавлена.")
            else:
                await event.reply("⚠️ Уже в списке.")
        else:
            await event.reply("❌ Ответь на сообщение из нужного чата.")

async def spam_loop():
    while True:
        queue = load_queue()
        if queue["messages"] and queue["targets"]:
            for msg_id in queue["messages"]:
                for chat_id in queue["targets"]:
                    try:
                        await client.forward_messages(chat_id, msg_id, entity="me")
                    except Exception as e:
                        print(f"[{datetime.now()}] Ошибка отправки: {e}")
        await asyncio.sleep(DELAY_MINUTES * 60)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована!")
        return

    print("✅ Бот запущен.")
    await spam_loop()

if __name__ == "__main__":
    asyncio.run(main())
