"""Git Repos Agent for handling repository operations."""
import os
import git
import logging
from pathlib import Path
from typing import List, Tuple
from src.logging_config import setup_logger

logger = setup_logger(__name__)

STANDARDS_REPO = "https://github.com/DEFRA/software-development-standards"
DATA_DIR = Path("data")
CODEBASE_DIR = DATA_DIR / "codebase"
STANDARDS_DIR = DATA_DIR / "standards"

# Files to exclude when flattening
EXCLUDED_FILES = {
    # Binary files
    '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip',
    # Package lock files
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'poetry.lock', 'Pipfile.lock', 'composer.lock',
    'Gemfile.lock', 'cargo.lock', 'packages.lock.json'
}

# Directories to exclude
EXCLUDED_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}


async def flatten_repository(repo_path: Path, output_file: Path) -> None:
    """Flatten a repository's files into a single text file."""
    logger.debug(f"Flattening repository at {repo_path} to {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(repo_path):
            # Modify dirs in place to exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for file in files:
                # Skip excluded files
                if any(file.endswith(ext) for ext in EXCLUDED_FILES) or any(file == excluded for excluded in EXCLUDED_FILES):
                    logger.debug(f"Skipping excluded file: {file}")
                    continue

                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as source_file:
                        relative_path = file_path.relative_to(repo_path)
                        f.write(f"\n# File: {relative_path}\n")
                        f.write(source_file.read())
                        f.write("\n")
                except (UnicodeDecodeError, IOError) as e:
                    logger.warning(f"Skipping file {file_path}: {str(e)}")


async def process_standards_repo(temp_dir: Path) -> List[Path]:
    """Process standards repository and save each file separately."""
    logger.debug("Processing standards repository")
    standards_files = []

    excluded_files = {'README.md', 'CONTRIBUTING.md'}
    valid_suffixes = ('_principles.md', '_standards.md')

    for root, _, files in os.walk(temp_dir):
        for file in files:
            if '.git' in root or file in excluded_files:
                continue
                
            if not any(file.endswith(suffix) for suffix in valid_suffixes):
                continue

            source_path = Path(root) / file
            try:
                with open(source_path, 'r', encoding='utf-8') as source_file:
                    content = source_file.read()

                output_file = STANDARDS_DIR / f"{file}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# File: {file}\n")
                    f.write(content)
                standards_files.append(output_file)
                logger.debug(f"Processed standards file: {file}")
            except (UnicodeDecodeError, IOError) as e:
                logger.warning(f"Skipping standards file {source_path}: {str(e)}")

    return standards_files


async def clone_repo(repo_url: str, target_dir: Path) -> None:
    """Clone a git repository to the target directory."""
    logger.debug(f"Cloning repository {repo_url} to {target_dir}")
    if target_dir.exists():
        logger.debug(f"Removing existing directory: {target_dir}")
        import shutil
        shutil.rmtree(target_dir)

    git.Repo.clone_from(repo_url, target_dir)


async def process_repositories(repository_url: str) -> Tuple[Path, List[Path]]:
    """Process both the code repository and standards repository."""
    import tempfile

    # Create necessary directories
    CODEBASE_DIR.mkdir(parents=True, exist_ok=True)
    STANDARDS_DIR.mkdir(parents=True, exist_ok=True)

    repo_name = repository_url.split('/')[-1].replace('.git', '')
    codebase_file = CODEBASE_DIR / f"{repo_name}.txt"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        code_repo_dir = temp_path / "code"
        standards_repo_dir = temp_path / "standards"

        # Clone and process code repository
        await clone_repo(repository_url, code_repo_dir)
        await flatten_repository(code_repo_dir, codebase_file)

        # Clone and process standards repository
        await clone_repo(STANDARDS_REPO, standards_repo_dir)
        standards_files = await process_standards_repo(standards_repo_dir)

        return codebase_file, standards_files
