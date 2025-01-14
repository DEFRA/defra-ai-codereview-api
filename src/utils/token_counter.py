import os
from pathlib import Path
import tiktoken


def count_repo_tokens(repo_path: str) -> tuple[int, int]:
    """
    Count characters and estimate tokens for all text files in repo

    Args:
        repo_path: Path to repository root

    Returns:
        tuple of (total_chars, estimated_tokens)
    """
    total_chars = 0
    excluded = {'.git', '__pycache__', '.pytest_cache',
                '*.pyc', '*.pyo', '*.pyd', '.DS_Store'}

    enc = tiktoken.get_encoding("cl100k_base")  # Claude's encoding

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in excluded]

        for file in files:
            if file.startswith('.') or any(file.endswith(ext) for ext in {'.pyc', '.pyo', '.pyd'}):
                continue

            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_chars += len(content)

            except (UnicodeDecodeError, PermissionError):
                continue

    # Rough estimate: 1 token ≈ 4 characters for code
    estimated_tokens = len(enc.encode(content))

    return total_chars, estimated_tokens
