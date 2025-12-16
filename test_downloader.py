"""
Downloader test skripti
YouTube va Instagram havolalarini test qilish
"""
import asyncio
import sys
sys.path.insert(0, '.')

from downloader import download_video, get_platform, clean_url

async def test_platform_detection():
    """Platform aniqlashni test qilish"""
    print("=" * 50)
    print("Platform aniqlash testi")
    print("=" * 50)
    
    test_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("https://www.instagram.com/reel/ABC123/", "instagram"),
        ("https://www.tiktok.com/@user/video/123", "tiktok"),
        ("https://www.facebook.com/watch/?v=123", "facebook"),
    ]
    
    for url, expected in test_urls:
        result = get_platform(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} {url[:40]}... -> {result} (kutilgan: {expected})")

async def test_url_cleaning():
    """URL tozalashni test qilish"""
    print("\n" + "=" * 50)
    print("URL tozalash testi")
    print("=" * 50)
    
    test_urls = [
        ("  https://youtube.com/watch?v=123  ", "https://youtube.com/watch?v=123"),
        ("https://threads.com/post/123", "https://threads.net/post/123"),
    ]
    
    for url, expected in test_urls:
        result = clean_url(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{url}' -> '{result}'")

async def test_download():
    """Haqiqiy yuklab olishni test qilish (qisqa YouTube video)"""
    print("\n" + "=" * 50)
    print("Download test (YouTube Shorts)")
    print("=" * 50)
    
    # Qisqa test video
    test_url = "https://www.youtube.com/shorts/N-tRXewCAmU"
    
    try:
        print(f"Yuklanmoqda: {test_url}")
        result = await download_video(test_url)
        if result:
            print(f"✅ Muvaffaqiyatli yuklandi: {result}")
            import os
            if os.path.exists(result):
                size = os.path.getsize(result) / 1024 / 1024
                print(f"   Fayl hajmi: {size:.2f} MB")
                os.remove(result)
                print("   Fayl o'chirildi")
        else:
            print("❌ Fayl qaytarilmadi")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

async def main():
    await test_platform_detection()
    await test_url_cleaning()
    
    # Haqiqiy download testini o'tkazish
    print("\nHaqiqiy download testini boshlashni xohlaysizmi? (y/n)")
    # Avtomatik test uchun shunchaki platform testini bajaramiz
    # await test_download()

if __name__ == "__main__":
    asyncio.run(main())
