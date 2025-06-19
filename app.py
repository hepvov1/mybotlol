import asyncio, re, json, os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

# 🔐 Настройки
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION"]

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Глобальные переменные
message_refs = []  # [(username, msg_id)]
forward_enabled = False
interval_minutes = 60
json_file = 'messages.json'
me_id = None

# === ФАЙЛ ===
def save_messages():
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(message_refs, f, ensure_ascii=False, indent=2)

def load_messages():
    global message_refs
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            message_refs = json.load(f)

# === ЧАТЫ ===
async def get_all_chats():
    result = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=100,
        hash=0
    ))
    return result.chats

# === ПЕРЕСЫЛКА ===
async def forward_once():
    if message_refs:
        print(f"🔁 Пересылаю {len(message_refs)} сообщений...")
        chats = await get_all_chats()
        for chat in chats:
            for username, msg_id in message_refs:
                try:
                    await client.forward_messages(chat.id, msg_id, from_peer=username)
                    print(f"✅ Отправлено: https://t.me/{username}/{msg_id} в {chat.title}")
                except Exception as e:
                    print(f"⚠️ Ошибка при пересылке в {chat.id}: {e}")

async def forward_loop():
    global forward_enabled
    while True:
        if forward_enabled and message_refs:
            await forward_once()
        await asyncio.sleep(interval_minutes * 60)

# === КОМАНДЫ ===
@client.on(events.NewMessage(pattern=r'\.botstart ?(\d+)?'))
async def start(event):
    if event.sender_id != me_id: return
    global forward_enabled, interval_minutes
    if event.pattern_match.group(1):
        interval_minutes = int(event.pattern_match.group(1))
    await forward_once()
    forward_enabled = True
    await event.reply(f"✅ Бот запущен. Пересылает каждые {interval_minutes} минут.")

@client.on(events.NewMessage(pattern=r'\.botstop'))
async def stop(event):
    if event.sender_id != me_id: return
    global forward_enabled
    forward_enabled = False
    await event.reply("🛑 Бот остановлен.")

@client.on(events.NewMessage(pattern=r'\.add (.+)'))
async def add_message(event):
    if event.sender_id != me_id: return
    url = event.pattern_match.group(1).strip()
    match = re.match(r'https?://t\.me/([^/]+)/(\d+)', url)
    if not match:
        await event.reply("⚠️ Неверная ссылка. Пример: `.add https://t.me/канал/123`")
        return
    username, msg_id = match.groups()
    message_refs.append((username, int(msg_id)))
    save_messages()
    await event.reply(f"✅ Добавлено сообщение {msg_id} из @{username}")


@client.on(events.NewMessage(pattern=r'\.delete (\d+)'))
async def delete_message(event):
    if event.sender_id != me_id: return
    index = int(event.pattern_match.group(1))
    if 0 <= index < len(message_refs):
        removed = message_refs.pop(index)
        save_messages()
        await event.reply(f"🗑️ Удалено: https://t.me/{removed[0]}/{removed[1]}")
    else:
        await event.reply("❌ Неверный индекс.")

@client.on(events.NewMessage(pattern=r'\.list'))
async def list_messages(event):
    if event.sender_id != me_id: return
    if not message_refs:
        await event.reply("📭 Список пуст.")
    else:
        text = "📋 Список сообщений:\n"
        for i, (username, msg_id) in enumerate(message_refs):
            text += f"{i}. https://t.me/{username}/{msg_id}\n"
        await event.reply(text)

@client.on(events.NewMessage(pattern=r'\.help'))
async def help_cmd(event):
    if event.sender_id != me_id: return
    await event.reply("""
📖 Команды:

.botstart [мин] — запустить пересылку
.botstop — остановить
.add <ссылка> — добавить сообщение
.delete <номер> — удалить сообщение
.list — список
.help — помощь
""")

# === ЗАПУСК ===
async def main():
    global me_id
    await client.start()
    me = await client.get_me()
    me_id = me.id
    print(f"✅ Вошёл как @{me.username or me.id}")
    load_messages()
    await asyncio.gather(
        client.run_until_disconnected(),
        forward_loop()
    )

if __name__ == '__main__':
    asyncio.run(main())
