import asyncio
from downloader import download_video

async def test():
    # 'Test Video' by YouTube Help
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo 
    print(f"Testing download for: {url}")
    path = await download_video(url)
    print(f"Download result: {path}")

if __name__ == "__main__":
    asyncio.run(test())
