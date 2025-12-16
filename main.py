import os
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from downloader import download_video, download_audio

# Logging ni yoqish (Render logs uchun stdout ga yozish)
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger().setLevel(logging.INFO)
print("Bot ishga tushmoqda...", flush=True)

# Bot tokenini shu yerga yozing yoki muhit o'zgaruvchisidan oling
BOT_TOKEN = "8522116634:AAHZYnKtOnllhkhBfjWkuCSx-Zmd7Elhk00"
# Adminlar ID ro'yxati (o'zingizning ID raqamingizni kiriting)
# ID ni olish uchun @userinfobot ga yozishingiz mumkin
ADMIN_IDS = [6040028347] 

# Bot username (reklama uchun)
BOT_USERNAME = "@UniversalDownloaduzb_bot"
# Video/Audio caption (reklama matni)
CAPTION_TEXT = "📹 Siz so'ragan video\n\n🤖 Bot: @UniversalDownloaduzb_bot\n👉 Obuna bo'ling!"
AUDIO_CAPTION_TEXT = "🎵 Siz so'ragan audio\n\n🤖 Bot: @UniversalDownloaduzb_bot\n👉 Obuna bo'ling!"

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
    reply_to_user = State()  # Foydalanuvchiga javob yozish

# Foydalanuvchi holatlari (dasturchiga xabar yuborish)
class UserState(StatesGroup):
    waiting_for_message = State()

dp = Dispatcher(storage=MemoryStorage())

# DB ni ishga tushirish
init_db()

# Asosiy tugmalar (keyboard)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟣 Instagram"), KeyboardButton(text="🖤 TikTok")],
        [KeyboardButton(text="🔴 YouTube"), KeyboardButton(text="🔵 Facebook")],
        [KeyboardButton(text="👨‍💻 Dasturchi"), KeyboardButton(text="🏠 Bosh menyu")],
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



@dp.message(F.text == "👨‍💻 Dasturchi")
async def about_handler(message: types.Message, state: FSMContext):
    text = ("👨‍💻 **Dasturchi bilan bog'lanish**\n\n"
            "Savolingiz yoki taklifingiz bo'lsa, pastga yozing.\n"
            "Xabaringiz adminga yuboriladi.\n\n"
            "❌ Bekor qilish uchun /cancel bosing.")
    await message.answer(text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(UserState.waiting_for_message)

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Hech narsa bekor qilinmadi.", reply_markup=main_kb)
        return
    await state.clear()
    await message.answer("✅ Bekor qilindi.", reply_markup=main_kb)

@dp.message(UserState.waiting_for_message)
async def receive_user_message(message: types.Message, state: FSMContext):
    user = message.from_user
    user_info = f"👤 **Foydalanuvchi:** {user.full_name}\n"
    user_info += f"🆔 **ID:** `{user.id}`\n"
    if user.username:
        user_info += f"📧 **Username:** @{user.username}\n"
    user_info += f"\n💬 **Xabar:**\n{message.text}"
    
    # Javob berish tugmasi
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Javob berish", callback_data=f"reply_{user.id}")]
    ])
    
    # Adminga yuborish
    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id, 
                f"📩 **Yangi xabar keldi!**\n\n{user_info}",
                parse_mode="Markdown",
                reply_markup=reply_kb
            )
            sent_count += 1
        except Exception as e:
            logging.error(f"Adminga xabar yuborishda xatolik ({admin_id}): {e}")
    
    if sent_count > 0:
        await message.answer(
            "✅ Xabaringiz adminga yuborildi!\n"
            "Tez orada javob olasiz.",
            reply_markup=main_kb
        )
    else:
        await message.answer(
            "❌ Xabar yuborishda xatolik yuz berdi.\n"
            "Iltimos keyinroq urinib ko'ring.",
            reply_markup=main_kb
        )
    
    await state.clear()

# Admin javob berish callback handleri
@dp.callback_query(F.data.startswith("reply_"))
async def reply_callback_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[1])
    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(AdminState.reply_to_user)
    
    await callback.message.answer(
        f"✍️ Foydalanuvchiga (ID: {user_id}) javob yozing:\n\n"
        "❌ Bekor qilish uchun /cancel bosing."
    )
    await callback.answer()

# Admin javob xabarini qabul qilish
@dp.message(AdminState.reply_to_user)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")
    
    if not user_id:
        await message.answer("❌ Xatolik: Foydalanuvchi topilmadi.", reply_markup=admin_kb)
        await state.clear()
        return
    
    try:
        await message.bot.send_message(
            user_id,
            f"💬 **Admin javobi:**\n\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer(f"✅ Javob foydalanuvchiga (ID: {user_id}) yuborildi!", reply_markup=admin_kb)
    except Exception as e:
        logging.error(f"Javob yuborishda xatolik: {e}")
        await message.answer(f"❌ Javob yuborishda xatolik: {e}", reply_markup=admin_kb)
    
    await state.clear()

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
    platform_name = "📹 Video"
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        platform_name = "🔴 YouTube"
    elif "instagram.com" in url.lower():
        platform_name = "🟣 Instagram"
    elif "tiktok.com" in url.lower():
        platform_name = "🖤 TikTok"
    elif "facebook.com" in url.lower() or "fb.watch" in url.lower():
        platform_name = "🔵 Facebook"

    # Video/Audio tanlash tugmalari
    # URL ni callback_data ga qo'shish (64 baytgacha limit)
    # Shuning uchun URL ni hash qilamiz
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    
    # URL ni vaqtincha saqlash (global dict)
    if not hasattr(download_handler, 'url_cache'):
        download_handler.url_cache = {}
    download_handler.url_cache[url_hash] = url
    
    choice_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data=f"dl_video_{url_hash}"),
            InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"dl_audio_{url_hash}")
        ]
    ])
    
    await message.answer(
        f"{platform_name} aniqlandi!\n\n"
        "Qanday formatda yuklab olmoqchisiz?",
        reply_markup=choice_kb
    )


# Video yuklash callback
@dp.callback_query(F.data.startswith("dl_video_"))
async def download_video_callback(callback: CallbackQuery):
    url_hash = callback.data.replace("dl_video_", "")
    
    # URL ni olish
    if not hasattr(download_handler, 'url_cache') or url_hash not in download_handler.url_cache:
        await callback.answer("❌ Havola topilmadi. Qaytadan yuboring.", show_alert=True)
        return
    
    url = download_handler.url_cache[url_hash]
    await callback.answer("Video yuklanmoqda...")
    
    # Xabarni yangilash
    await callback.message.edit_text("🎬 Video yuklanmoqda... ⏳\nIltimos kuting, bu biroz vaqt olishi mumkin.")
    
    try:
        video_path = await download_video(url)
        
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            file_size_mb = file_size / (1024 * 1024)
            max_size = 50 * 1024 * 1024
            
            if file_size > max_size:
                await callback.message.edit_text(
                    f"⚠️ Video hajmi juda katta ({file_size_mb:.1f} MB).\n\n"
                    "Telegram botlari 50 MB gacha fayl yuborishi mumkin.\n"
                    "Iltimos, qisqaroq video tanlang."
                )
                os.remove(video_path)
                return
            
            await callback.message.edit_text(f"✅ Video topildi ({file_size_mb:.1f} MB), jo'natilmoqda...")
            video_file = FSInputFile(video_path)
            await callback.message.answer_video(video_file, caption=CAPTION_TEXT)
            
            try:
                os.remove(video_path)
            except:
                pass
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ Videoni yuklab bo'lmadi.")
            
    except Exception as e:
        error_text = str(e)
        if error_text.startswith("❌"):
            await callback.message.edit_text(error_text)
        else:
            await callback.message.edit_text(f"❌ Xatolik: {error_text[:150]}")


# Audio yuklash callback
@dp.callback_query(F.data.startswith("dl_audio_"))
async def download_audio_callback(callback: CallbackQuery):
    url_hash = callback.data.replace("dl_audio_", "")
    
    # URL ni olish
    if not hasattr(download_handler, 'url_cache') or url_hash not in download_handler.url_cache:
        await callback.answer("❌ Havola topilmadi. Qaytadan yuboring.", show_alert=True)
        return
    
    url = download_handler.url_cache[url_hash]
    await callback.answer("Audio yuklanmoqda...")
    
    # Xabarni yangilash
    await callback.message.edit_text("🎵 Audio (MP3) yuklanmoqda... ⏳\nIltimos kuting.")
    
    try:
        audio_path = await download_audio(url)
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)
            
            await callback.message.edit_text(f"✅ Audio topildi ({file_size_mb:.1f} MB), jo'natilmoqda...")
            audio_file = FSInputFile(audio_path)
            await callback.message.answer_audio(audio_file, caption=AUDIO_CAPTION_TEXT)
            
            try:
                os.remove(audio_path)
            except:
                pass
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ Audioni yuklab bo'lmadi.")
            
    except Exception as e:
        error_text = str(e)
        if error_text.startswith("❌"):
            await callback.message.edit_text(error_text)
        else:
            await callback.message.edit_text(f"❌ Xatolik: {error_text[:150]}")


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
    print("=" * 50, flush=True)
    print("Bot ishga tushmoqda...", flush=True)
    print("=" * 50, flush=True)
    
    bot = Bot(token=BOT_TOKEN)
    
    # Web serverni ishga tushirish (orqa fonda)
    await start_web_server()
    print("Web server tayyor!", flush=True)
    
    print("Telegram polling boshlanmoqda...", flush=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Main.py ishga tushdi!", flush=True)
    
    if BOT_TOKEN == "SIZNING_BOT_TOKENINGIZ_BU_YERDA":
        print("DIQQAT: Bot tokeni kiritilmagan! main.py faylida BOT_TOKEN ni o'zgartiring.")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi.")
    except Exception as e:
        print(f"XATOLIK: {e}", flush=True)
        raise

