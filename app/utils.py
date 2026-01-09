import os
from .config import IGNORE_EXTENSIONS, IGNORE_FILES, IGNORE_DIRS

def is_useful_file(path: str) -> bool:
    """Check if a file should be included in the LLM context."""
    name = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    
    # Check directories
    parts = path.split('/')
    if any(d in parts for d in IGNORE_DIRS):
        return False
        
    if name in IGNORE_FILES: return False
    if ext in IGNORE_EXTENSIONS: return False
    return True

def github_to_raw_url(repo_url: str, file_path: str) -> str:
    """
    Converts a GitHub blob URL to a raw content URL.
    Example: https://github.com/user/repo/blob/main/file.py 
    -> https://raw.githubusercontent.com/user/repo/main/file.py
    """
    # Simply replace github.com with raw.githubusercontent.com and remove /blob/
    # This assumes standard GitHub URL structure
    raw_base = repo_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return f"{raw_base}/{file_path}"
