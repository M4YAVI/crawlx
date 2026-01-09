# Repo2Context

A powerful tool to convert entire GitHub repositories into a single, LLM-optimized context file (`.txt`). Built with **FastHTML**, **Crawl4AI**, and **TailwindCSS**.

## Features

- **Intelligent Pruning**: Automatically ignores `node_modules`, `.git`, images, and lock files.
- **Batched Crawling**: Uses `AsyncWebCrawler` (Crawl4AI) to fetch files in parallel.
- **Clean Output**: wraps code in clear `--- START OF FILE ---` blocks.
- **Sleek UI**: Dark mode interface with real-time progress streaming.

## Setup

1. **Install Dependencies**:
   ```powershell
   uv sync
   # or
   uv pip install -r requirements.txt
   ```

2. **Run the App**:
   ```powershell
   uv run python main.py
   ```

3. **Open Browser**:
   Navigate to `http://localhost:5001`.

## Troubleshooting

### Windows: NotImplementedError
If you see a `NotImplementedError` regarding the event loop, it is because Playwright requires the `ProactorEventLoop` on Windows. This project includes a fix in `main.py`:

```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**Note**: This fix must remain at the very top of `main.py` before any other imports.
