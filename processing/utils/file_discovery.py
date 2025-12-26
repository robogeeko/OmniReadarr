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

    all_audio_dirs: list[tuple[str, int]] = []
    all_ebook_files: list[str] = []

    ebook_extensions = [
        ".epub",
        ".mobi",
        ".azw",
        ".azw3",
        ".pdf",
        ".txt",
        ".rtf",
        ".fb2",
        ".lit",
    ]
    audio_extensions = [
        ".mp3",
        ".m4a",
        ".m4b",
        ".flac",
        ".ogg",
        ".wav",
        ".aac",
        ".opus",
    ]

    release_title_lower = release_title.lower()
    release_title_words = release_title_lower.split()

    for root, dirs, files in os.walk(completed_downloads_path):
        audio_files_in_dir = []
        ebook_files_in_dir = []

        for file in files:
            file_path = os.path.join(root, file)
            file_lower = file.lower()

            is_ebook = any(file_lower.endswith(ext) for ext in ebook_extensions)
            is_audio = any(file_lower.endswith(ext) for ext in audio_extensions)

            if is_ebook:
                ebook_files_in_dir.append((file_path, file_lower))
            elif is_audio:
                audio_files_in_dir.append((file_path, file_lower))

        if download_client_id:
            download_client_id_lower = download_client_id.lower()
            for file_path, file_lower in ebook_files_in_dir:
                if download_client_id_lower in file_lower:
                    logger.info(
                        f"Found ebook file matching download_client_id: {file_path}"
                    )
                    return file_path

            for file_path, file_lower in audio_files_in_dir:
                if download_client_id_lower in file_lower:
                    logger.info(
                        f"Found audio directory matching download_client_id: {root}"
                    )
                    return root

        for file_path, file_lower in ebook_files_in_dir:
            all_ebook_files.append(file_path)
            if release_title_lower in file_lower:
                logger.info(f"Found ebook file matching release_title: {file_path}")
                return file_path

        if audio_files_in_dir:
            release_title_words_filtered = [
                word
                for word in release_title_words
                if word
                not in [
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "of",
                    "in",
                    "on",
                    "at",
                    "to",
                    "for",
                ]
                and not word.isdigit()
                and len(word) > 2
            ]

            matching_audio_files = []
            for file_path, file_lower in audio_files_in_dir:
                if release_title_lower in file_lower:
                    matching_audio_files.append(file_path)
                    continue

                file_words = (
                    file_lower.replace(".", " ")
                    .replace("_", " ")
                    .replace("-", " ")
                    .split()
                )
                file_words_filtered = [
                    w
                    for w in file_words
                    if w
                    not in [
                        "ch",
                        "chapter",
                        "part",
                        "ep",
                        "episode",
                        "the",
                        "a",
                        "an",
                        "and",
                        "or",
                        "of",
                    ]
                    and not w.isdigit()
                    and len(w) > 2
                ]

                if (
                    len(release_title_words_filtered) >= 2
                    and len(file_words_filtered) >= 2
                ):
                    matches = sum(
                        1
                        for word in release_title_words_filtered[:5]
                        if word in file_words_filtered
                    )
                    if matches >= 2:
                        matching_audio_files.append(file_path)
                        continue

                if len(release_title_words_filtered) >= 1:
                    for title_word in release_title_words_filtered[:3]:
                        if len(title_word) > 3 and title_word in file_lower:
                            matching_audio_files.append(file_path)
                            break

            if matching_audio_files:
                logger.info(
                    f"Found audio directory with {len(matching_audio_files)} matching files "
                    f"(out of {len(audio_files_in_dir)} total) in: {root}"
                )
                return root

            root_name_lower = os.path.basename(root).lower()
            root_words = (
                root_name_lower.replace(".", " ")
                .replace("_", " ")
                .replace("-", " ")
                .split()
            )
            root_words_filtered = [
                w
                for w in root_words
                if w
                not in [
                    "ch",
                    "chapter",
                    "part",
                    "ep",
                    "episode",
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "of",
                ]
                and not w.isdigit()
                and len(w) > 2
            ]

            if len(release_title_words_filtered) >= 2 and len(root_words_filtered) >= 2:
                matches = sum(
                    1
                    for word in release_title_words_filtered[:5]
                    if word in root_words_filtered
                )
                if matches >= 2:
                    logger.info(
                        f"Found audio directory matching release_title by directory name: {root}"
                    )
                    return root

            if len(audio_files_in_dir) >= 1:
                all_audio_dirs.append((root, len(audio_files_in_dir)))

    if all_audio_dirs:
        best_match = max(all_audio_dirs, key=lambda x: x[1])
        logger.info(
            f"Found audio directory with {best_match[1]} audio files "
            f"(assuming audiobook with multiple chapters): {best_match[0]}"
        )
        return best_match[0]

    logger.warning(
        f"No matching files found. Searched in: {completed_downloads_path}, "
        f"release_title: {release_title}, download_client_id: {download_client_id}. "
        f"Found {len(all_audio_dirs)} directories with audio files, "
        f"{len(all_ebook_files)} ebook files total."
    )

    raise FileDiscoveryError(
        f"Could not find downloaded file for release_title: {release_title}"
    )
