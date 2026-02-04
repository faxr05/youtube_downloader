import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(TOKEN)
dp = Dispatcher()

user_links = {}        # user_id : link
progress_msg = {}     # user_id : message_id


# ================= HELPERS =================
def file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)


async def send_any_file(user_id, path, file_type="video"):
    file = FSInputFile(path)

    if file_size_mb(path) <= 50:
        if file_type == "video":
            await bot.send_video(user_id, video=file)
        else:
            await bot.send_audio(user_id, audio=file)
    else:
        await bot.send_document(
            user_id,
            document=file,
            caption="📎 Fayl katta (50MB+), document sifatida yuborildi"
        )


# ================= /start =================
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Salom!\n\n"
        "🔗 YouTube link yuboring\n"
        "🎥 Video yoki 🎵 Audio qilib yuklab beraman\n"
        "🚀 2GB gacha qo‘llab-quvvatlanadi"
    )


# ================= LINK =================
@dp.message(F.text.contains("youtube") | F.text.contains("youtu.be"))
async def link_handler(message: Message):
    user_links[message.from_user.id] = message.text

    kb = InlineKeyboardBuilder()
    kb.button(text="🎥 Video", callback_data="video")
    kb.button(text="🎵 Audio (MP3)", callback_data="audio")

    await message.answer(
        "⬇️ Formatni tanlang:",
        reply_markup=kb.as_markup()
    )


# ================= FORMAT =================
@dp.callback_query(F.data.in_(["video", "audio"]))
async def format_handler(call: CallbackQuery):
    msg = await call.message.answer("⏳ Iltimos kuting!")
    progress_msg[call.from_user.id] = msg.message_id

    if call.data == "audio":
        await download_audio(call)
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="360p", callback_data="360")
        kb.button(text="720p", callback_data="720")

        await call.message.answer(
            "🎥 Video sifati:",
            reply_markup=kb.as_markup()
        )


# ================= QUALITY =================
@dp.callback_query(F.data.in_(["360", "720"]))
async def quality_handler(call: CallbackQuery):
    msg = await call.message.answer("⏳ Iltimos kuting!")
    progress_msg[call.from_user.id] = msg.message_id
    await download_video(call, call.data)


# ================= PROGRESS =================
async def update_progress(user_id, percent):
    try:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=progress_msg[user_id],
            text=f"⏳ Yuklanmoqda... {percent}%"
        )
    except:
        pass


# ================= AUDIO =================
async def download_audio(call: CallbackQuery):
    user_id = call.from_user.id
    url = user_links[user_id]

    def hook(d):
        if d['status'] == 'downloading':
            percent = int(float(d['_percent_str'].replace('%','')))
            asyncio.run_coroutine_threadsafe(
                update_progress(user_id, percent),
                asyncio.get_event_loop()
            )

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "progress_hooks": [hook],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        path = ydl.prepare_filename(info).replace(".webm", ".mp3")

    await send_any_file(user_id, path, "audio")
    os.remove(path)


# ================= VIDEO =================
async def download_video(call: CallbackQuery, quality):
    user_id = call.from_user.id
    url = user_links[user_id]

    if quality == "360":
        ydl_format = "bestvideo[height<=360]+bestaudio/best"
    else:
        ydl_format = "bestvideo[height<=720]+bestaudio/best"

    def hook(d):
        if d['status'] == 'downloading' and '_percent_str' in d:
            percent = int(float(d['_percent_str'].replace('%','')))
            asyncio.run_coroutine_threadsafe(
                update_progress(user_id, percent),
                asyncio.get_event_loop()
            )

    ydl_opts = {
        "format": ydl_format,
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "progress_hooks": [hook]
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        path = ydl.prepare_filename(info)
        if not path.endswith(".mp4"):
            path = path.rsplit(".", 1)[0] + ".mp4"

    await send_any_file(user_id, path, "video")
    os.remove(path)

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
