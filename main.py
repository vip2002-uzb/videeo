import os
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from downloader import download_video

# Logging ni yoqish
logging.basicConfig(level=logging.INFO)

# Bot tokenini shu yerga yozing yoki muhit o'zgaruvchisidan oling
BOT_TOKEN = "8522116634:AAHZYnKtOnllhkhBfjWkuCSx-Zmd7Elhk00"
# Adminlar ID ro'yxati (o'zingizning ID raqamingizni kiriting)
# ID ni olish uchun @userinfobot ga yozishingiz mumkin
ADMIN_IDS = [6040028347] 

# Ma'lumotlar bazasini ulash
def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Admin holatlari
class AdminState(StatesGroup):
    broadcast_text = State()

dp = Dispatcher(storage=MemoryStorage())

# DB ni ishga tushirish
init_db()

# Asosiy tugmalar (keyboard)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟣 Instagram"), KeyboardButton(text="🖤 TikTok")],
        [KeyboardButton(text="🔴 YouTube"), KeyboardButton(text="🔵 Facebook")],
        [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="👨‍💻 Dasturchi")],
        [KeyboardButton(text="🏠 Bosh menyu")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Linkni yuboring..."
)

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    add_user(message.from_user.id)
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!\n"
                         f"Men Instagram, Facebook, YouTube, TikTok va Threads dan video yuklovchi botman.\n"
                         f"Menga video havolasini (link) yuboring yoki kerakli platformani tanlang.", reply_markup=main_kb)

@dp.message(F.text == "🏠 Bosh menyu")
async def menu_handler(message: types.Message):
    await command_start_handler(message)

@dp.message(F.text == "🟣 Instagram")
async def instagram_handler(message: types.Message):
    await message.answer("Instagramdan video yuklash uchun menga post yoki reels havolasini yuboring.")

@dp.message(F.text == "🖤 TikTok")
async def tiktok_handler(message: types.Message):
    await message.answer("TikTokdan video yuklash uchun menga video havolasini yuboring.")

@dp.message(F.text == "🔴 YouTube")
async def youtube_handler(message: types.Message):
    await message.answer("YouTubedan video yuklash uchun menga video yoki shorts havolasini yuboring.")

@dp.message(F.text == "🔵 Facebook")
async def facebook_handler(message: types.Message):
    await message.answer("Facebookdan video yuklash uchun menga video havolasini yuboring.")

@dp.message(F.text == "ℹ️ Yordam")
async def help_handler(message: types.Message):
    text = ("🤖 **Botdan foydalanish:**\n\n"
            "Instagram, TikTok, YouTube, Facebook yoki Threads dan video havolasini (link) nusxalab oling va menga yuboring.\n"
            "Men videoni yuklab, sizga jo'nataman.")
    await message.answer(text, parse_mode="Markdown", reply_markup=main_kb)

@dp.message(F.text == "👨‍💻 Dasturchi")
async def about_handler(message: types.Message):
    await message.answer("Bu bot Universal Video Downloader.\nSavollar bo'lsa admin bilan bog'laning.", reply_markup=main_kb)

# --- Admin Panel Logic ---

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="✉️ Xabar yuborish")],
        [KeyboardButton(text="🏠 Bosh menyu")]
    ],
    resize_keyboard=True
)

@dp.message(Command("admin"))
async def admin_panel_handler(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Admin panelga xush kelibsiz!", reply_markup=admin_kb)
    else:
        await message.answer("Siz admin emassiz.")

@dp.message(F.text == "📊 Statistika")
async def stats_handler(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        users = get_all_users()
        await message.answer(f"📊 Bot foydalanuvchilari soni: {len(users)} ta")

@dp.message(F.text == "✉️ Xabar yuborish")
async def broadcast_start_handler(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Foydalanuvchilarga yuboriladigan xabarni kiriting (matn, rasm yoki video):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AdminState.broadcast_text)

@dp.message(AdminState.broadcast_text)
async def broadcast_send_handler(message: types.Message, state: FSMContext):
    users = get_all_users()
    count = 0
    
    await message.answer(f"Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")
    
    for user_id in users:
        try:
            await message.send_copy(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05) # Spamdan saqlanish uchun ozgina kutish
        except Exception as e:
            logging.error(f"Foydalanuvchiga xabar yuborishda xatolik ({user_id}): {e}")
            
    await message.answer(f"Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi.", reply_markup=admin_kb)
    await state.clear()

# -------------------------

@dp.message()
async def download_handler(message: types.Message):
    url = message.text
    if not url.startswith(("http", "www")):
        await message.answer("Iltimos, to'g'ri havola yuboring.")
        return

    # Qaysi platform ekanligini aniqlash
    platform_emoji = "📹"
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        platform_emoji = "🔴 YouTube"
    elif "instagram.com" in url.lower():
        platform_emoji = "🟣 Instagram"
    elif "tiktok.com" in url.lower():
        platform_emoji = "🖤 TikTok"
    elif "facebook.com" in url.lower() or "fb.watch" in url.lower():
        platform_emoji = "🔵 Facebook"

    status_msg = await message.answer(f"{platform_emoji} video yuklanmoqda... ⏳\nIltimos kuting, bu biroz vaqt olishi mumkin.")

    try:
        # Videoni yuklab olish
        video_path = await download_video(url)
        
        if video_path and os.path.exists(video_path):
            # Fayl hajmini tekshirish
            file_size = os.path.getsize(video_path)
            max_size = 50 * 1024 * 1024  # 50 MB (Telegram limiti)
            
            if file_size > max_size:
                await status_msg.edit_text("⚠️ Video hajmi juda katta (50 MB dan ortiq). Telegram bu hajmni qo'llab-quvvatlamaydi.")
                os.remove(video_path)
                return
            
            await status_msg.edit_text("✅ Video topildi, jo'natilmoqda...")
            video_file = FSInputFile(video_path)
            await message.answer_video(video_file, caption=f"Siz so'ragan video 📹\n\n@video_downloader_botingiz_nomi")
            
            # Faylni o'chirib tashlash (joyni tejash uchun)
            try:
                os.remove(video_path)
            except:
                pass
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Kechirasiz, videoni yuklab bo'lmadi.\n\nSabablari:\n• Havola noto'g'ri\n• Video shaxsiy\n• Platforma muammosi")
            
    except Exception as e:
        error_text = str(e)
        # Xatolik xabarini chiroyli qilish
        if error_text.startswith("❌"):
            await status_msg.edit_text(error_text)
        else:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi:\n\n{error_text[:200]}")


# Web server funksiyasi (Render uchun)
async def health_check(request):
    return web.Response(text="Bot is online!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    bot = Bot(token=BOT_TOKEN)
    # Web serverni ishga tushirish (orqa fonda)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import sys
    if BOT_TOKEN == "SIZNING_BOT_TOKENINGIZ_BU_YERDA":
        print("DIQQAT: Bot tokeni kiritilmagan! main.py faylida BOT_TOKEN ni o'zgartiring.")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
