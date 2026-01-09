import os
import asyncio
import traceback
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from .utils import is_useful_file, github_to_raw_url

async def crawl_repo(repo_url: str):
    """
    Generator that streams status updates and the final file processing.
    Refined with SKILL.md best practices.
    """
    repo_url = repo_url.rstrip("/")
    if "blob" in repo_url: 
        repo_url = repo_url.split("/blob/")[0]
    elif "tree" in repo_url:
        repo_url = repo_url.split("/tree/")[0]

    yield "ID: 🚀 Starting Repo Scan...\n"
    
    # Text mode is faster, but verbose=True helps debug
    # Defaulting to a standard user agent to avoid bot detection (per SKILL.md)
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        viewport_width=1280,
        viewport_height=800,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            yield f"INFO: Crawling {repo_url} for file list...\n"
            
            # 1. Get File List
            # Standard config with JS enabled
            try:
                list_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    page_timeout=30000
                )
                result = await crawler.arun(url=repo_url, config=list_config)
            except Exception as e:
                yield f"ERROR: Crawler failed to start: {str(e)}\nTraceback: {traceback.format_exc()}\n"
                return

            if not result.success:
                yield f"ERROR: Failed to crawl repo: {result.error_message}\n"
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
                 yield "ERROR: No relevant files found. Is this a public repo?\n"
                 return

            yield f"INFO: Found {len(unique_files)} logic-relevant files.\n"

            # 2. Extract Content
            # We use raw.githubusercontent for speed and reliability
            raw_urls = [github_to_raw_url(repo_url, f) for f in unique_files]
            
            yield "INFO: Extracting code into context...\n"
            
            # Optimized Run Config for extraction
            extract_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS
            )
            
            full_context = []
            chunk_size = 10
            total_files = len(raw_urls)
            
            for i in range(0, total_files, chunk_size):
                chunk_urls = raw_urls[i:i+chunk_size]
                chunk_paths = unique_files[i:i+chunk_size]
                
                yield f"INFO: Processing batch {i+1}-{min(i+chunk_size, total_files)}/{total_files}...\n"
                
                try:
                    # Using arun_many as per SKILL.md recommendation for batch processing
                    batch_results = await crawler.arun_many(
                        urls=chunk_urls, 
                        config=extract_config
                    )
                    
                    for j, res in enumerate(batch_results):
                        file_path = chunk_paths[j]
                        if res.success:
                            file_header = f"\n\n--- START OF FILE: {file_path} ---\n"
                            # Use markdown as per SKILL.md recommendation
                            content = res.markdown if res.markdown else res.html
                            
                            full_context.append(file_header + content + f"\n--- END OF FILE: {file_path} ---")
                            yield f"PROGRESS: Bundled {file_path}\n"
                        else:
                            yield f"PROGRESS: Failed {file_path} ({res.error_message})\n"
                except Exception as e:
                    yield f"ERROR: Batch processing failed: {str(e)}\nTraceback: {traceback.format_exc()}\n"

            final_text = "".join(full_context)
            
            # Save File
            os.makedirs("static", exist_ok=True)
            filename = f"llm_context_{repo_url.split('/')[-1]}.txt"
            file_path = os.path.join("static", filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_text)
                
            yield f"DONE: {filename}\n"

    except Exception as e:
        yield f"ERROR: Critical Crawler Error: {str(e)}\nTraceback: {traceback.format_exc()}\n"
