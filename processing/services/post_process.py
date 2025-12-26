from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from core.models_processing import ProcessingConfiguration
from downloaders.models import DownloadAttempt
from processing.utils.ebook_converter import EbookConverterError, convert_to_epub
from processing.utils.file_discovery import FileDiscoveryError, find_downloaded_file

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

