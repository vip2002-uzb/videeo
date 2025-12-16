import yt_dlp
import os
import uuid
import asyncio
import imageio_ffmpeg
import logging
import re

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_platform(url: str) -> str:
    """Havoladan platformani aniqlash"""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    elif "threads.net" in url_lower or "threads.com" in url_lower:
        return "threads"
    else:
        return "unknown"

def clean_url(url: str) -> str:
    """URLni tozalash va to'g'irlash"""
    # Bo'shliqlarni olib tashlash
    url = url.strip()
    
    # Threads domenini to'g'irlash
    if "threads.com" in url:
        url = url.replace("threads.com", "threads.net")
    
    # Instagram reels/post havolalarini to'g'irlash
    if "instagram.com" in url:
        # /reel/ -> /reels/ ga o'zgartirish (agar kerak bo'lsa)
        url = re.sub(r'/reel/', '/reels/', url)
    
    return url

async def download_video(url: str) -> str:
    """
    Berilgan havoladan videoni yuklab oladi va fayl yo'lini qaytaradi.
    YouTube, Instagram, TikTok, Facebook, Threads qo'llab-quvvatlanadi.
    """
    url = clean_url(url)
    platform = get_platform(url)
    logger.info(f"Platform aniqlandi: {platform}, URL: {url}")
    
    output_filename = f"downloads/{uuid.uuid4()}"
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Asosiy yt-dlp sozlamalari
    base_opts = {
        'outtmpl': f'{output_filename}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ffmpeg_location': ffmpeg_path,
        'merge_output_format': 'mp4',
        'file_access_retries': 50,
        'fragment_retries': 50,
        'retries': 50,
        'socket_timeout': 30,
        'extractor_retries': 5,
        # Cookiefayli mavjud bo'lsa ishlatamiz
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }
    
    # Platforma bo'yicha sozlamalar
    if platform == "youtube":
        ydl_opts = {
            **base_opts,
            # YouTube uchun 480p (50MB limitiga sig'ishi uchun)
            # Agar 480p bo'lmasa, eng yaqin past sifatni oladi
            'format': 'best[height<=480][ext=mp4]/best[height<=480]/best[height<=720][ext=mp4]/best[height<=720]/best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
    elif platform == "instagram":
        ydl_opts = {
            **base_opts,
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }
    elif platform == "tiktok":
        ydl_opts = {
            **base_opts,
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
    elif platform == "facebook":
        ydl_opts = {
            **base_opts,
            'format': 'bestvideo+bestaudio/best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
    else:
        # Boshqa platformalar uchun umumiy sozlamalar
        ydl_opts = {
            **base_opts,
            'format': 'bestvideo+bestaudio/best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
    
    # None qiymatlarni olib tashlash
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    try:
        loop = asyncio.get_running_loop()
        
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Video yuklab olinmoqda: {url}")
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # Agar fayl .mp4 kengaytmasi bilan tugamasa, to'g'rilash
                if not file_path.endswith('.mp4'):
                    mp4_path = f"{output_filename}.mp4"
                    if os.path.exists(mp4_path):
                        file_path = mp4_path
                
                logger.info(f"Video muvaffaqiyatli yuklandi: {file_path}")
                return file_path

        file_path = await loop.run_in_executor(None, run_download)
        
        # Fayl mavjudligini tekshirish
        if file_path and os.path.exists(file_path):
            return file_path
        
        # .mp4 fayl bo'lsa uni qaytarish
        mp4_fallback = f"{output_filename}.mp4"
        if os.path.exists(mp4_fallback):
            return mp4_fallback
            
        raise Exception("Video fayli yuklanmadi")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"yt-dlp xatolik: {error_msg}")
        
        # Xatolik turlarini aniqlash va foydalanuvchiga tushunarli xabar berish
        if "Sign in to confirm" in error_msg or "age" in error_msg.lower():
            raise Exception("❌ Bu video yosh chegarasi bilan himoyalangan. Yuklab bo'lmaydi.")
        elif "Private video" in error_msg:
            raise Exception("❌ Bu video shaxsiy (private) va ko'rib bo'lmaydi.")
        elif "Video unavailable" in error_msg:
            raise Exception("❌ Bu video mavjud emas yoki o'chirilgan.")
        elif "HTTP Error 403" in error_msg:
            raise Exception("❌ Kirish taqiqlangan. Havola noto'g'ri bo'lishi mumkin.")
        elif "HTTP Error 429" in error_msg:
            raise Exception("❌ Juda ko'p so'rovlar yuborildi. Iltimos, biroz kuting va qaytadan urinib ko'ring.")
        elif "no video formats" in error_msg.lower():
            raise Exception("❌ Bu havolada video topilmadi. Havola to'g'ri ekanligini tekshiring.")
        elif "Unable to extract" in error_msg:
            raise Exception("❌ Video ma'lumotlarini chiqarib bo'lmadi. Havola noto'g'ri bo'lishi mumkin.")
        elif "login required" in error_msg.lower() or "logged in" in error_msg.lower():
            raise Exception("❌ Bu videoni ko'rish uchun login talab qilinadi.")
        else:
            raise Exception(f"❌ Yuklab bo'lmadi: {error_msg[:100]}")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Umumiy xatolik: {error_msg}")
        
        # Windows fayl band xatoligi
        if "[WinError 32]" in error_msg:
            logger.info("Windows fayl band xatoligi, kutilmoqda...")
            await asyncio.sleep(2)
            
            final_path = f"{output_filename}.mp4"
            temp_path = f"{output_filename}.temp.mp4"
            
            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, final_path)
                    logger.info("Temp fayl muvaffaqiyatli qayta nomlandi")
                    return final_path
                except:
                    pass
            
            if os.path.exists(final_path):
                return final_path
        
        raise e


async def download_audio(url: str) -> str:
    """
    Berilgan havoladan faqat audio (MP3) yuklab oladi.
    """
    url = clean_url(url)
    platform = get_platform(url)
    logger.info(f"Audio yuklanmoqda - Platform: {platform}, URL: {url}")
    
    output_filename = f"downloads/{uuid.uuid4()}"
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_filename}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ffmpeg_location': ffmpeg_path,
        # MP3 ga o'zgartirish
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
    }
    
    # Cookies fayli mavjud bo'lsa
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        loop = asyncio.get_running_loop()
        
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Audio yuklab olinmoqda: {url}")
                info = ydl.extract_info(url, download=True)
                # MP3 fayl nomi
                base_path = ydl.prepare_filename(info)
                # Kengaytmani .mp3 ga o'zgartirish
                mp3_path = os.path.splitext(base_path)[0] + '.mp3'
                logger.info(f"Audio muvaffaqiyatli yuklandi: {mp3_path}")
                return mp3_path

        file_path = await loop.run_in_executor(None, run_download)
        
        if file_path and os.path.exists(file_path):
            return file_path
        
        # Fallback - .mp3 fayl qidirish
        mp3_fallback = f"{output_filename}.mp3"
        if os.path.exists(mp3_fallback):
            return mp3_fallback
            
        raise Exception("Audio fayli yuklanmadi")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"yt-dlp audio xatolik: {error_msg}")
        
        if "Sign in to confirm" in error_msg:
            raise Exception("❌ Bu audio yosh chegarasi bilan himoyalangan.")
        elif "Private video" in error_msg:
            raise Exception("❌ Bu video shaxsiy (private).")
        elif "Video unavailable" in error_msg:
            raise Exception("❌ Bu video mavjud emas yoki o'chirilgan.")
        else:
            raise Exception(f"❌ Audio yuklab bo'lmadi: {error_msg[:100]}")
            
    except Exception as e:
        logger.error(f"Audio yuklashda xatolik: {e}")
        raise e
