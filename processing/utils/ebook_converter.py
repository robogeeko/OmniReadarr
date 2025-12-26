from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class EbookConverterError(Exception):
    pass


def convert_to_epub(
    input_path: str, output_path: str, ebook_convert_path: str = "ebook-convert"
) -> str:
    if not os.path.exists(input_path):
        raise EbookConverterError(f"Input file does not exist: {input_path}")

    input_ext = Path(input_path).suffix.lower()
    if input_ext == ".epub":
        logger.info(f"File is already EPUB format: {input_path}")
        return input_path

    logger.info(
        f"Converting {input_path} to EPUB using {ebook_convert_path}, "
        f"output: {output_path}"
    )

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        result = subprocess.run(
            [ebook_convert_path, input_path, output_path],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        logger.info(f"Conversion successful: {output_path}")
        logger.debug(f"Conversion output: {result.stdout}")

        if not os.path.exists(output_path):
            raise EbookConverterError(
                f"Conversion completed but output file not found: {output_path}"
            )

        return output_path
    except subprocess.TimeoutExpired:
        raise EbookConverterError(
            f"Conversion timed out after 300 seconds for: {input_path}"
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or "Unknown error"
        raise EbookConverterError(
            f"Conversion failed for {input_path}: {error_msg}"
        )
    except FileNotFoundError:
        raise EbookConverterError(
            f"ebook-convert not found at: {ebook_convert_path}. "
            f"Please install Calibre or configure the correct path."
        )

