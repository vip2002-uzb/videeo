import yt_dlp
import asyncio

def list_formats(url):
    ydl_opts = {
        'listformats': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=False)

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=i5V7uL_Mg6I"
    try:
        list_formats(url)
    except Exception as e:
        print(e)
