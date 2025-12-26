from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class FileOrganizerError(Exception):
    pass


def sanitize_filename(name: str, max_length: int = 200) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", name)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = sanitized.strip()
    sanitized = sanitized.strip(".")
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    
    if not sanitized:
        sanitized = "Unknown"
    
    return sanitized


def get_library_path(
    library_base_path: str, author: str, book_title: str
) -> tuple[str, str]:
    sanitized_author = sanitize_filename(author) if author else "Unknown Author"
    sanitized_title = sanitize_filename(book_title) if book_title else "Unknown Title"
    
    library_dir = os.path.join(library_base_path, sanitized_author, sanitized_title)
    return library_dir, sanitized_title


def organize_to_library(
    source_file_path: str,
    library_base_path: str,
    author: str,
    book_title: str,
) -> str:
    if not os.path.exists(source_file_path):
        raise FileOrganizerError(f"Source file does not exist: {source_file_path}")
    
    if not os.path.exists(library_base_path):
        raise FileOrganizerError(
            f"Library base path does not exist: {library_base_path}"
        )
    
    library_dir, sanitized_title = get_library_path(
        library_base_path, author, book_title
    )
    
    logger.info(
        f"Organizing file to library - source: {source_file_path}, "
        f"library_dir: {library_dir}, sanitized_title: {sanitized_title}"
    )
    
    os.makedirs(library_dir, exist_ok=True)
    
    source_ext = Path(source_file_path).suffix
    dest_filename = f"{sanitized_title}{source_ext}"
    dest_path = os.path.join(library_dir, dest_filename)
    
    if os.path.exists(dest_path) and os.path.samefile(source_file_path, dest_path):
        logger.info(f"File already at destination: {dest_path}")
        return dest_path
    
    shutil.copy2(source_file_path, dest_path)
    logger.info(f"Copied file to library: {dest_path}")
    
    return dest_path


def organize_directory_to_library(
    source_dir_path: str,
    library_base_path: str,
    author: str,
    book_title: str,
) -> str:
    if not os.path.exists(source_dir_path):
        raise FileOrganizerError(f"Source directory does not exist: {source_dir_path}")
    
    if not os.path.isdir(source_dir_path):
        raise FileOrganizerError(f"Source path is not a directory: {source_dir_path}")
    
    if not os.path.exists(library_base_path):
        raise FileOrganizerError(
            f"Library base path does not exist: {library_base_path}"
        )
    
    library_dir, sanitized_title = get_library_path(
        library_base_path, author, book_title
    )
    
    logger.info(
        f"Organizing directory to library - source: {source_dir_path}, "
        f"library_dir: {library_dir}, sanitized_title: {sanitized_title}"
    )
    
    os.makedirs(library_dir, exist_ok=True)
    
    audio_extensions = [".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".wav", ".aac", ".opus"]
    files_copied = 0
    
    for root, dirs, files in os.walk(source_dir_path):
        for file in files:
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in audio_extensions):
                source_file = os.path.join(root, file)
                dest_file = os.path.join(library_dir, file)
                
                if os.path.exists(dest_file) and os.path.samefile(source_file, dest_file):
                    continue
                
                shutil.copy2(source_file, dest_file)
                files_copied += 1
                logger.info(f"Copied audio file to library: {dest_file}")
    
    if files_copied == 0:
        raise FileOrganizerError(
            f"No audio files found in source directory: {source_dir_path}"
        )
    
    logger.info(f"Copied {files_copied} audio files to library: {library_dir}")
    
    return library_dir

