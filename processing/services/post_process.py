from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from core.models_processing import ProcessingConfiguration
from downloaders.models import DownloadAttempt
from processing.utils.cover_downloader import CoverDownloadError, download_cover
from processing.utils.ebook_converter import EbookConverterError, convert_to_epub
from processing.utils.file_discovery import FileDiscoveryError, find_downloaded_file
from processing.utils.file_organizer import (
    FileOrganizerError,
    organize_directory_to_library,
    organize_to_library,
)
from processing.utils.metadata_generator import generate_opf

logger = logging.getLogger(__name__)


class PostProcessingError(Exception):
    pass


def convert_to_epub_for_attempt(attempt_id: UUID) -> dict[str, str | bool]:
    try:
        attempt = DownloadAttempt.objects.select_related("download_client").get(
            id=attempt_id
        )
    except DownloadAttempt.DoesNotExist:
        return {"success": False, "error": f"Download attempt {attempt_id} not found"}


    config = ProcessingConfiguration.objects.filter(enabled=True).first()
    if not config:
        return {
            "success": False,
            "error": "No enabled processing configuration found",
        }

    input_file_path: str | None = None

    if attempt.raw_file_path and os.path.exists(attempt.raw_file_path):
        input_file_path = attempt.raw_file_path
        logger.info(f"Using existing raw_file_path: {input_file_path}")
    else:
        try:
            input_file_path = find_downloaded_file(
                completed_downloads_path=config.completed_downloads_path,
                release_title=attempt.release_title,
                download_client_id=attempt.download_client_download_id,
            )
            attempt.raw_file_path = input_file_path
            attempt.save(update_fields=["raw_file_path"])
            logger.info(f"Found downloaded file: {input_file_path}")
        except FileDiscoveryError as e:
            return {"success": False, "error": str(e)}

    input_ext = Path(input_file_path).suffix.lower()
    if input_ext == ".epub":
        attempt.post_processed_file_path = input_file_path
        attempt.save(update_fields=["post_processed_file_path"])
        return {
            "success": True,
            "message": f"File is already EPUB format: {input_file_path}",
        }

    output_file_path = str(Path(input_file_path).with_suffix(".epub"))

    try:
        epub_path = convert_to_epub(
            input_path=input_file_path,
            output_path=output_file_path,
            ebook_convert_path=config.calibre_ebook_convert_path,
        )
        attempt.post_processed_file_path = epub_path
        attempt.save(update_fields=["post_processed_file_path"])
        return {
            "success": True,
            "message": f"Successfully converted to EPUB: {epub_path}",
        }
    except EbookConverterError as e:
        return {"success": False, "error": str(e)}


def organize_to_library_for_attempt(attempt_id: UUID) -> dict[str, str | bool]:
    try:
        attempt = DownloadAttempt.objects.select_related("download_client").get(
            id=attempt_id
        )
    except DownloadAttempt.DoesNotExist:
        return {"success": False, "error": f"Download attempt {attempt_id} not found"}

    media = attempt.media
    if not media:
        return {"success": False, "error": "Media not found for download attempt"}

    config = ProcessingConfiguration.objects.filter(enabled=True).first()
    if not config:
        return {
            "success": False,
            "error": "No enabled processing configuration found",
        }

    file_to_organize: str | None = None

    if attempt.post_processed_file_path and os.path.exists(
        attempt.post_processed_file_path
    ):
        file_to_organize = attempt.post_processed_file_path
        logger.info(f"Using post-processed file: {file_to_organize}")
    elif attempt.raw_file_path and os.path.exists(attempt.raw_file_path):
        file_to_organize = attempt.raw_file_path
        logger.info(f"Using raw file: {file_to_organize}")
    else:
        try:
            file_to_organize = find_downloaded_file(
                completed_downloads_path=config.completed_downloads_path,
                release_title=attempt.release_title,
                download_client_id=attempt.download_client_download_id,
            )
            attempt.raw_file_path = file_to_organize
            attempt.save(update_fields=["raw_file_path"])
            logger.info(f"Found downloaded file: {file_to_organize}")
        except FileDiscoveryError as e:
            return {"success": False, "error": str(e)}

    author = media.authors[0] if media.authors else "Unknown Author"

    try:
        if os.path.isdir(file_to_organize):
            library_file_path = organize_directory_to_library(
                source_dir_path=file_to_organize,
                library_base_path=config.library_base_path,
                author=author,
                book_title=media.title,
            )
        else:
            library_file_path = organize_to_library(
                source_file_path=file_to_organize,
                library_base_path=config.library_base_path,
                author=author,
                book_title=media.title,
            )
        logger.info(f"File organized to library: {library_file_path}")
    except FileOrganizerError as e:
        return {"success": False, "error": str(e)}

    sanitized_title = Path(library_file_path).stem
    library_dir = Path(library_file_path).parent
    opf_path = os.path.join(library_dir, f"{sanitized_title}.opf")

    try:
        generate_opf(media, opf_path)
        logger.info(f"Generated OPF file: {opf_path}")
    except Exception as e:
        logger.warning(f"Failed to generate OPF file: {str(e)}")

    cover_path: str | None = None
    if media.cover_url:
        cover_output_path = os.path.join(library_dir, f"{sanitized_title}.jpg")
        try:
            download_cover(media.cover_url, cover_output_path)
            cover_path = cover_output_path
            logger.info(f"Downloaded cover to: {cover_path}")
        except CoverDownloadError as e:
            logger.warning(f"Failed to download cover: {str(e)}")

    media.library_path = library_file_path
    if cover_path:
        media.cover_path = cover_path
    media.save(update_fields=["library_path", "cover_path"])

    attempt.post_processed_file_path = library_file_path
    attempt.save(update_fields=["post_processed_file_path"])

    return {
        "success": True,
        "message": f"Successfully organized to library: {library_file_path}",
    }

