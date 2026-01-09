# Intelligent Filtering Constants
IGNORE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot',
    '.mp4', '.pdf', '.zip', '.gz', '.tar', '.lock', '.pyc', '.exe', '.bin', '.ipynb'
}

IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'poetry.lock', 'pnpm-lock.yaml',
    '.gitignore', '.DS_Store', 'LICENSE', 'MANIFEST.in', 'uv.lock'
}

IGNORE_DIRS = {
    'node_modules', '.git', '.github', '__pycache__', 'venv', 'env', 'dist', 'build', '.venv', 'target'
}
