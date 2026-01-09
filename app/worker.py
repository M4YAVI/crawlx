#!/usr/bin/env python3
"""
Repo2Context Crawler Worker
Standalone script that handles all Crawl4AI operations.
Called as a subprocess to avoid asyncio conflicts with the web server.
"""
import sys
import os
import asyncio

# --- CRITICAL: WINDOWS ASYNCIO FIX ---
# Applied at the very top, before ANY imports that might touch asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# --- Configuration ---
IGNORE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp', '.bmp',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.lock', '.sum', '.mod',
}
IGNORE_FILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '.gitignore', '.dockerignore', 'LICENSE', 'Makefile'}
IGNORE_DIRS = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', '.cache'}

def is_useful_file(path: str) -> bool:
    """Filter out non-code files."""
    path_lower = path.lower()
    if any(f"/{d}/" in path_lower or path_lower.endswith(f"/{d}") for d in IGNORE_DIRS):
        return False
    if any(path_lower.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return False
    if path.split('/')[-1] in IGNORE_FILES:
        return False
    return True

def github_to_raw_url(repo_url: str, file_path: str) -> str:
    """Convert GitHub file path to raw content URL."""
    parts = repo_url.replace("https://github.com/", "").split("/")
    owner, repo = parts[0], parts[1]
    branch_and_path = file_path.split("/", 1)
    branch = branch_and_path[0]
    path = branch_and_path[1] if len(branch_and_path) > 1 else ""
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

async def crawl_repo(repo_url: str):
    """Main crawling logic."""
    repo_url = repo_url.rstrip("/")
    if "blob" in repo_url:
        repo_url = repo_url.split("/blob/")[0]
    elif "tree" in repo_url:
        repo_url = repo_url.split("/tree/")[0]

    print("STATUS:Starting repository scan...", flush=True)

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        viewport_width=1280,
        viewport_height=800,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"STATUS:Fetching file list from {repo_url}...", flush=True)

        # Step 1: Get repository file list
        list_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=30000)
        result = await crawler.arun(url=repo_url, config=list_config)

        if not result.success:
            print(f"ERROR:Failed to crawl repo: {result.error_message}", flush=True)
            return

        links = result.links.get("internal", [])
        file_paths = []
        for link in links:
            href = link.get("href", "")
            if "/blob/" in href and is_useful_file(href):
                parts = href.split("/blob/")
                if len(parts) > 1:
                    file_paths.append(parts[1])

        unique_files = sorted(list(set(file_paths)))
        if not unique_files:
            print("ERROR:No relevant files found. Is this a public repository?", flush=True)
            return

        print(f"STATUS:Found {len(unique_files)} code files.", flush=True)

        # Step 2: Fetch file contents
        raw_urls = [github_to_raw_url(repo_url, f) for f in unique_files]
        extract_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        full_context = []
        total = len(raw_urls)

        for i in range(0, total, 10):
            batch_urls = raw_urls[i:i+10]
            batch_paths = unique_files[i:i+10]
            print(f"STATUS:Processing files {i+1}-{min(i+10, total)} of {total}...", flush=True)

            batch_results = await crawler.arun_many(urls=batch_urls, config=extract_config)

            for j, res in enumerate(batch_results):
                path = batch_paths[j]
                if res.success:
                    content = res.markdown if res.markdown else res.html
                    full_context.append(f"\n\n--- START OF FILE: {path} ---\n{content}\n--- END OF FILE: {path} ---")
                    print(f"PROGRESS:{path}", flush=True)
                else:
                    print(f"WARNING:Failed to fetch {path}", flush=True)

        # Step 3: Save output
        os.makedirs("static", exist_ok=True)
        repo_name = repo_url.split("/")[-1]
        filename = f"llm_context_{repo_name}.txt"
        filepath = os.path.join("static", filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("".join(full_context))

        print(f"DONE:{filename}", flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR:Usage: python worker.py <github_repo_url>", flush=True)
        sys.exit(1)

    repo_url = sys.argv[1]
    asyncio.run(crawl_repo(repo_url))
