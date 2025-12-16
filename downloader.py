import yt_dlp
import os
import uuid
import asyncio
import imageio_ffmpeg

async def download_video(url: str) -> str:
    """
    Berilgan havoladan videoni yuklab oladi va fayl yo'lini qaytaradi.
    """
    # URL ni tozalash va to'g'irlash
    if "threads.com" in url:
        url = url.replace("threads.com", "threads.net")
    
    output_filename = f"downloads/{uuid.uuid4()}"
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    # Endi ffmpeg borligi uchun eng yaxshi sifatni (video+audio) yuklay olamiz
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', 
        'outtmpl': f'{output_filename}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ffmpeg_location': ffmpeg_path,
        'merge_output_format': 'mp4',
        # Windows tizimida fayl band bo'lib qolish holatlari uchun qo'shimcha urinishlar
        'file_access_retries': 50,
        'fragment_retries': 50,
        'retries': 50,
        # 429 (Too Many Requests) xatoligini oldini olish uchun "User-Agent" ni o'zgartiramiz
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
    }

    # Cookies fayli borligini tekshirish (yosh chegarasi yoki login talab qilinadigan videolar uchun)
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = "cookies.txt"

    try:
        # Asinxron muhitda bloklanmasligi uchun
        loop = asyncio.get_running_loop()
        
        def run_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        file_path = await loop.run_in_executor(None, run_info)
        return file_path

    except Exception as e:
        error_msg = str(e)
        # Windowsda 'WinError 32' (fayl band) xatoligi bo'lsa, qo'lda to'g'irlashga harakat qilamiz
        if "[WinError 32]" in error_msg:
            print(f"Windows fayl band xatoligi ushlandi, tuzatishga urinilmoqda...")
            await asyncio.sleep(2) # Antivirus yoki tizim faylni bo'shatishini kutamiz
            
            # Tahminiy temp fayl nomlari
            final_path = f"{output_filename}.mp4"
            temp_path = f"{output_filename}.temp.mp4"
            
            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, final_path)
                    print("Temp fayl muvaffaqiyatli qayta nomlandi.")
                    return final_path
                except Exception as rename_error:
                    print(f"Qayta nomlashda xatolik: {rename_error}")

        if "Sign in to confirm" in error_msg:
            print("Xatolik: YouTube cookies talab qilmoqda.")
            raise Exception("YouTube bot ekanligimizni aniqladi. Iltimos, 'cookies.txt' faylini yangilang yoki qo'shing.")

        print(f"Yuklashda xatolik: {e}")
        # Xatoni chaqiruvchi funksiyaga qaytarish, shunda userga aniqroq xabar boradi
        raise e
