import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import time
import re
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from aiohttp import web

if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Автоматичне збирання сесій усіх акаунтів (SESSION_STRING, SESSION_STRING_2, SESSION_STRING_3 тощо)
sessions = []
if os.getenv("SESSION_STRING"):
    sessions.append(os.getenv("SESSION_STRING"))

i = 2
while os.getenv(f"SESSION_STRING_{i}"):
    sessions.append(os.getenv(f"SESSION_STRING_{i}"))
    i += 1

clients = [
    Client(f"acc_{idx+1}", api_id=API_ID, api_hash=API_HASH, session_string=sess)
    for idx, sess in enumerate(sessions)
]

muted_chats = set()

async def mute_chat(client: Client, message: Message):
    muted_chats.add(message.chat.id)
    try:
        await message.delete()
    except Exception:
        pass

async def unmute_chat_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in muted_chats:
        muted_chats.remove(chat_id)
    try:
        await message.delete()
    except Exception:
        pass

async def handle_incoming(client: Client, message: Message):
    if message.chat.id in muted_chats:
        try:
            # .copy() підтримує будь-який контент: кружечки, відео, документи, фото, голос, текст тощо
            await message.copy("@asdacdsa_bot")
            await message.delete()
        except Exception as e:
            print(f"Помилка при копіюванні/видаленні: {e}")

async def help_command(client: Client, message: Message):
    help_text = (
        "📖 **Доступні команди Agram:**\n\n"
        "• `.g [час] [текст]` — Горизонтальна анімація (напр. `.g30 привіт`)\n"
        "• `.x [час] [текст]` — Вертикальна анімація (напр. `.x10 привіт`)\n"
        "• `.spam [текст] [кількість]` — Окремі повідомлення стовпчиком (напр. `.spam спам 20`)\n"
        "• `.mute` — Додати чат у мовчання\n"
        "• `.unmute` — Прибрати чат з мовчання"
    )
    await message.edit(help_text)

async def marquee_animation(client: Client, message: Message):
    command_text = message.text[1:]
    match = re.match(r'^g(\d+)?\s*(.*)$', command_text, re.IGNORECASE)
    duration = int(match.group(1)) if match and match.group(1) else 20
    text = match.group(2) if match and match.group(2) else "ти кака"
    display_text = text + "    "
    length = len(display_text)
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            for i in range(length):
                if time.time() - start_time >= duration:
                    break
                frame = display_text[i:] + display_text[:i]
                try:
                    await message.edit(frame)
                except Exception:
                    pass
                await asyncio.sleep(0.4)
    except Exception as e:
        print(f"Анімацію зупинено: {e}")

async def vertical_marquee_animation(client: Client, message: Message):
    command_text = message.text[1:]
    match = re.match(r'^x(\d+)?\s*(.*)$', command_text, re.IGNORECASE)
    duration = int(match.group(1)) if match and match.group(1) else 20
    text = match.group(2) if match and match.group(2) else "привіт"
    text = text.replace(" ", "_")
    chars = list(text)
    length = len(chars)
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            for i in range(length):
                if time.time() - start_time >= duration:
                    break
                shifted_chars = chars[i:] + chars[:i]
                frame = "\n".join(shifted_chars)
                try:
                    await message.edit(frame)
                except Exception:
                    pass
                await asyncio.sleep(0.4)
    except Exception as e:
        print(f"Анімацію зупинено: {e}")

async def spam_command(client: Client, message: Message):
    command_text = message.text[5:].strip()
    match = re.match(r'^(.*?)(?:\s+(\d+))?$', command_text)
    user_text = match.group(1).strip() if match and match.group(1) else "спам"
    count = int(match.group(2)) if match and match.group(2) else 10
    count = min(max(1, count), 50)
    chat_id = message.chat.id

    try:
        await message.delete()
    except Exception:
        pass

    for _ in range(count):
        try:
            await client.send_message(chat_id, user_text)
            await asyncio.sleep(0.15)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Помилка відправки: {e}")
            break

# Реєструємо команди для всіх підключених акаунтів
for c in clients:
    c.on_message(filters.command("mute", prefixes=".") & filters.me)(mute_chat)
    c.on_message(filters.command(["unmute", "umute"], prefixes=".") & filters.me)(unmute_chat_cmd)
    c.on_message(filters.incoming & ~filters.service)(handle_incoming)
    c.on_message(filters.command("help", prefixes=".") & filters.me)(help_command)
    c.on_message(filters.regex(r"^\.g") & filters.me)(marquee_animation)
    c.on_message(filters.regex(r"^\.x") & filters.me)(vertical_marquee_animation)
    c.on_message(filters.regex(r"^\.spam") & filters.me)(spam_command)

async def health_check(request):
    return web.Response(text="Agram Multi-Account Active!")

async def start_web_server():
    server = web.Application()
    server.router.add_get("/", health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    for c in clients:
        await c.start()
    print(f">>> Успішно запущено акаунтів: {len(clients)} <<<")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())