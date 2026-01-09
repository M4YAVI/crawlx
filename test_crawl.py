import sys
import asyncio

# Apply fix immediately
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.crawler import crawl_repo

async def run_test():
    repo_url = "https://github.com/M4YAVI/text-ocr"  # User's reported failing repo
    print(f"Testing crawl for {repo_url}...")
    
    try:
        async for chunk in crawl_repo(repo_url):
            # Print only key events to keep output clean
            if "INFO:" in chunk or "ERROR:" in chunk or "DONE:" in chunk:
                print(chunk.strip())
            elif "PROGRESS:" in chunk:
                 print(".", end="", flush=True)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
