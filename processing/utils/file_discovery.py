from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class FileDiscoveryError(Exception):
    pass


def find_downloaded_file(
    completed_downloads_path: str,
    release_title: str,
    download_client_id: str | None = None,
) -> str:
    if not os.path.exists(completed_downloads_path):
        raise FileDiscoveryError(
            f"Completed downloads path does not exist: {completed_downloads_path}"
        )

    if not os.path.isdir(completed_downloads_path):
        raise FileDiscoveryError(
            f"Completed downloads path is not a directory: {completed_downloads_path}"
        )

    logger.info(
        f"Searching for downloaded file in: {completed_downloads_path}, "
        f"release_title: {release_title}, download_client_id: {download_client_id}"
    )

    ebook_extensions = [".epub", ".mobi", ".azw", ".azw3", ".pdf", ".txt", ".rtf", ".fb2", ".lit"]

    for root, dirs, files in os.walk(completed_downloads_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_lower = file.lower()

            if any(file_lower.endswith(ext) for ext in ebook_extensions):
                if download_client_id and download_client_id in file:
                    logger.info(f"Found file matching download_client_id: {file_path}")
                    return file_path

                if release_title.lower() in file_lower:
                    logger.info(f"Found file matching release_title: {file_path}")
                    return file_path

    raise FileDiscoveryError(
        f"Could not find downloaded file for release_title: {release_title}"
    )

