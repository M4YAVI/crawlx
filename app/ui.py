import asyncio
import sys

# --- CRITICAL: FIX FOR WINDOWS ASYNCIO EVENT LOOP ---
# This must be here because uvicorn worker imports this module directly
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fasthtml.common import *
from starlette.responses import StreamingResponse
from .crawler import crawl_repo

# Setup App
headers = (
    Script(src="https://cdn.tailwindcss.com"),
    Link(href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css", rel="stylesheet"),
    Style("""
        body { background-color: #0f172a; color: #e2e8f0; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .gradient-text { background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        #logs::-webkit-scrollbar { width: 8px; }
        #logs::-webkit-scrollbar-track { background: #1e293b; }
        #logs::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
    """)
)

app, rt = fast_app(hdrs=headers)

@rt('/')
def get():
    return Body(
        Div(
            # Header
            Header(
                H1("Repo2Context", cls="text-5xl font-extrabold mb-2 gradient-text"),
                P("Convert entire GitHub repos into single-file LLM context.", cls="text-slate-400"),
                cls="text-center mb-10"
            ),
            
            # Form
            Form(
                Div(
                    I(cls="fab fa-github absolute left-4 top-1/2 -translate-y-1/2 text-2xl text-slate-500"),
                    Input(
                        type="text", 
                        name="repo_url", 
                        id="repo_url", 
                        required=True,
                        placeholder="https://github.com/unclecode/crawl4ai",
                        cls="w-full bg-slate-900 border border-slate-700 rounded-2xl py-4 pl-14 pr-4 focus:ring-2 focus:ring-sky-500 outline-none transition-all text-lg"
                    ),
                    cls="relative"
                ),
                Button(
                    "Generate Context File",
                    type="submit",
                    cls="w-full bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 py-4 rounded-2xl font-bold text-xl shadow-lg transform active:scale-95 transition-all mt-6"
                ),
                id="crawlForm",
                cls="space-y-6"
            ),
            
            # Status Container
            Div(
                Div(
                    Span("Initializing...", id="statusText", cls="text-sm font-medium text-sky-400 animate-pulse"),
                    cls="flex items-center justify-center mb-2"
                ),
                Div(
                    Div(id="progressBar", cls="bg-sky-500 h-2 rounded-full transition-all duration-500", style="width: 5%"),
                    cls="w-full bg-slate-800 rounded-full h-2"
                ),
                Div(id="logs", cls="bg-black/50 rounded-xl p-4 h-48 overflow-y-auto font-mono text-xs text-slate-500 space-y-1 mt-4"),
                id="statusContainer",
                cls="mt-8 hidden space-y-4"
            ),
            
            # Download Area
            Div(
                A(
                    I(cls="fas fa-download"), " Download llm-full.txt",
                    id="downloadBtn",
                    href="#",
                    download=True,
                    cls="flex items-center justify-center gap-3 w-full bg-emerald-600 hover:bg-emerald-500 py-4 rounded-2xl font-bold text-xl transition-all"
                ),
                id="downloadArea",
                cls="mt-8 hidden"
            ),
            
            cls="max-w-3xl w-full glass rounded-3xl p-8 shadow-2xl"
        ),
        
        # Javascript Client
        Script("""
        const form = document.getElementById('crawlForm');
        const statusContainer = document.getElementById('statusContainer');
        const logs = document.getElementById('logs');
        const progressBar = document.getElementById('progressBar');
        const statusText = document.getElementById('statusText');
        const downloadArea = document.getElementById('downloadArea');
        const downloadBtn = document.getElementById('downloadBtn');

        form.onsubmit = async (e) => {
            e.preventDefault();
            statusContainer.classList.remove('hidden');
            downloadArea.classList.add('hidden');
            logs.innerHTML = '';
            statusText.textContent = 'Initializing...';
            progressBar.style.width = '5%';
            
            const formData = new FormData(form);
            const response = await fetch('/process', { method: 'POST', body: formData });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\\n');
                
                lines.forEach(line => {
                    if (!line.trim()) return;
                    
                    if (line.startsWith('PROGRESS:')) {
                        const log = document.createElement('div');
                        log.textContent = `+ ${line.replace('PROGRESS:', '')}`;
                        logs.appendChild(log);
                        logs.scrollTop = logs.scrollHeight;
                        
                        let currentWidth = parseFloat(progressBar.style.width) || 5;
                        if (currentWidth < 90) progressBar.style.width = (currentWidth + 1) + '%';
                        
                    } else if (line.startsWith('INFO:')) {
                        statusText.textContent = line.replace('INFO:', '');
                    } else if (line.startsWith('ERROR:')) {
                        const log = document.createElement('div');
                        log.style.color = '#ef4444';
                        log.textContent = line;
                        logs.appendChild(log);
                    } else if (line.startsWith('DONE:')) {
                        const filename = line.replace('DONE:', '').trim();
                        downloadArea.classList.remove('hidden');
                        downloadBtn.href = `/static/${filename}`;
                        statusText.textContent = 'Process Complete!';
                        progressBar.style.width = '100%';
                    }
                });
            }
        };
        """),
        cls="min-h-screen flex flex-col items-center justify-center p-4"
    )

@rt('/process')
async def post(request: Request):
    form = await request.form()
    repo_url = form.get('repo_url')
    if not repo_url:
        return "Error: Missing repo_url"
    
    return StreamingResponse(crawl_repo(repo_url), media_type="text/event-stream")
