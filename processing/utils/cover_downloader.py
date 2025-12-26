from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class CoverDownloadError(Exception):
    pass


def download_cover(cover_url: str, output_path: str, timeout: int = 10) -> str:
    if not cover_url:
        raise CoverDownloadError("Cover URL is empty")
    
    logger.info(f"Downloading cover from {cover_url} to {output_path}")
    
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(cover_url)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    f"Unexpected content type for cover: {content_type}. "
                    f"Proceeding anyway."
                )
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            if not os.path.exists(output_path):
                raise CoverDownloadError(
                    f"Cover file was not written to {output_path}"
                )
            
            logger.info(f"Successfully downloaded cover to {output_path}")
            return output_path
            
    except httpx.HTTPStatusError as e:
        raise CoverDownloadError(
            f"HTTP error downloading cover: {e.response.status_code}"
        )
    except httpx.TimeoutException:
        raise CoverDownloadError(f"Timeout downloading cover after {timeout} seconds")
    except Exception as e:
        raise CoverDownloadError(f"Failed to download cover: {str(e)}")

