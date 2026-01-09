"""
Repo2Context v2 - Web Server
Uses subprocess to run the crawler, avoiding asyncio conflicts.
"""
from fasthtml.common import *
from starlette.responses import StreamingResponse
import subprocess
import sys
import os

# Premium dark-mode CSS
CUSTOM_CSS = """
:root {
    --bg-dark: #0a0a0f;
    --glass-bg: rgba(20, 20, 35, 0.7);
    --glass-border: rgba(255, 255, 255, 0.08);
    --accent-cyan: #00d4ff;
    --accent-purple: #7c3aed;
    --accent-pink: #ec4899;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-dark);
    color: var(--text-primary);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background-image: 
        radial-gradient(ellipse at 20% 20%, rgba(124, 58, 237, 0.15), transparent 50%),
        radial-gradient(ellipse at 80% 80%, rgba(0, 212, 255, 0.1), transparent 50%);
}

.container {
    width: 100%;
    max-width: 600px;
}

.card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    padding: 3rem;
    backdrop-filter: blur(20px);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.logo {
    text-align: center;
    margin-bottom: 2rem;
}

.logo h1 {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.logo p {
    color: var(--text-secondary);
    margin-top: 0.5rem;
}

.input-group {
    position: relative;
    margin-bottom: 1.5rem;
}

.input-group input {
    width: 100%;
    padding: 1rem 1rem 1rem 3rem;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    color: var(--text-primary);
    font-size: 1rem;
    transition: all 0.3s ease;
}

.input-group input:focus {
    outline: none;
    border-color: var(--accent-cyan);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
}

.input-group .icon {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary);
}

.btn-primary {
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
}

.btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

#status-area {
    margin-top: 2rem;
    display: none;
}

#status-text {
    color: var(--accent-cyan);
    font-weight: 500;
    margin-bottom: 1rem;
}

.progress-container {
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 1rem;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
    border-radius: 3px;
    width: 0%;
    transition: width 0.3s ease;
}

#log-area {
    background: rgba(0, 0, 0, 0.4);
    border-radius: 8px;
    padding: 1rem;
    max-height: 200px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.log-entry { margin-bottom: 0.25rem; }
.log-entry.error { color: #ef4444; }
.log-entry.success { color: #22c55e; }

#download-area {
    margin-top: 1.5rem;
    display: none;
}

.btn-download {
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: block;
    text-align: center;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading { animation: pulse 1.5s infinite; }
"""

# JavaScript for handling the form and streaming
CLIENT_JS = """
async function processRepo(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button');
    const input = form.querySelector('input');
    const statusArea = document.getElementById('status-area');
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    const logArea = document.getElementById('log-area');
    const downloadArea = document.getElementById('download-area');
    const downloadLink = document.getElementById('download-link');

    // Reset UI
    btn.disabled = true;
    btn.textContent = 'Processing...';
    statusArea.style.display = 'block';
    downloadArea.style.display = 'none';
    logArea.innerHTML = '';
    progressBar.style.width = '0%';

    try {
        const response = await fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'repo_url=' + encodeURIComponent(input.value)
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fileCount = 0;
        let totalEstimate = 10;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value);
            const lines = text.split('\\n').filter(l => l.trim());

            for (const line of lines) {
                if (line.startsWith('STATUS:')) {
                    statusText.textContent = line.substring(7);
                    statusText.classList.add('loading');
                } else if (line.startsWith('PROGRESS:')) {
                    fileCount++;
                    const pct = Math.min((fileCount / totalEstimate) * 100, 95);
                    progressBar.style.width = pct + '%';
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    entry.textContent = '✓ ' + line.substring(9);
                    logArea.appendChild(entry);
                    logArea.scrollTop = logArea.scrollHeight;
                } else if (line.startsWith('DONE:')) {
                    const filename = line.substring(5);
                    progressBar.style.width = '100%';
                    statusText.textContent = 'Complete!';
                    statusText.classList.remove('loading');
                    downloadLink.href = '/static/' + filename;
                    downloadLink.download = filename;
                    downloadArea.style.display = 'block';
                } else if (line.startsWith('ERROR:')) {
                    const entry = document.createElement('div');
                    entry.className = 'log-entry error';
                    entry.textContent = '✗ ' + line.substring(6);
                    logArea.appendChild(entry);
                    statusText.textContent = 'Error occurred';
                    statusText.classList.remove('loading');
                } else if (line.startsWith('WARNING:')) {
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    entry.textContent = '⚠ ' + line.substring(8);
                    logArea.appendChild(entry);
                }
            }
        }
    } catch (err) {
        statusText.textContent = 'Connection error: ' + err.message;
        statusText.classList.remove('loading');
    }

    btn.disabled = false;
    btn.textContent = 'Generate Context File';
}
"""

# FastHTML App
app = FastHTML(
    hdrs=(
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono&display=swap"),
        Style(CUSTOM_CSS),
    )
)
rt = app.route

@rt('/')
def get():
    return Html(
        Head(Title("Repo2Context")),
        Body(
            Div(
                Div(
                    Div(
                        H1("Repo2Context"),
                        P("Convert GitHub repos into LLM-ready context files"),
                        cls="logo"
                    ),
                    Form(
                        Div(
                            Span("🔗", cls="icon"),
                            Input(
                                type="text",
                                name="repo_url",
                                placeholder="https://github.com/owner/repo",
                                required=True
                            ),
                            cls="input-group"
                        ),
                        Button("Generate Context File", type="submit", cls="btn-primary"),
                        onsubmit="processRepo(event); return false;"
                    ),
                    Div(
                        P(id="status-text"),
                        Div(Div(id="progress-bar", cls="progress-bar"), cls="progress-container"),
                        Div(id="log-area"),
                        id="status-area"
                    ),
                    Div(
                        A("⬇️ Download Context File", href="#", id="download-link", cls="btn-download"),
                        id="download-area"
                    ),
                    cls="card"
                ),
                cls="container"
            ),
            Script(CLIENT_JS)
        )
    )

@rt('/process')
async def post(request):
    form = await request.form()
    repo_url = form.get('repo_url', '')

    if not repo_url:
        async def error_gen():
            yield "ERROR:Missing repository URL\n"
        return StreamingResponse(error_gen(), media_type="text/plain")

    def run_worker():
        """Run worker.py as subprocess using sync Popen (avoids asyncio issues)."""
        worker_path = os.path.join(os.path.dirname(__file__), "worker.py")
        
        process = subprocess.Popen(
            [sys.executable, worker_path, repo_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )

        for line in iter(process.stdout.readline, ''):
            yield line

        process.wait()

    return StreamingResponse(run_worker(), media_type="text/plain")

# Static file serving
@rt('/static/{filename}')
async def static_file(filename: str):
    from starlette.responses import FileResponse
    filepath = os.path.join("static", filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    return "File not found", 404
