from __future__ import annotations

import os
from uuid import UUID

from django.contrib.contenttypes.models import ContentType

from core.models import Media, MediaStatus
from downloaders.clients.sabnzbd import SABnzbdClient
from downloaders.models import (
    BlacklistReason,
    DownloadAttempt,
    DownloadAttemptStatus,
    DownloadBlacklist,
    DownloadClientConfiguration,
)
from indexers.prowlarr.client import ProwlarrClient
from indexers.prowlarr.results import SearchResult


class DownloadServiceError(Exception):
    pass


class DownloadService:
    def __init__(
        self,
        prowlarr_client: ProwlarrClient | None = None,
        sabnzbd_client_factory: type[SABnzbdClient] | None = None,
    ):
        if prowlarr_client is None:
            prowlarr_client = ProwlarrClient()
        self.prowlarr_client = prowlarr_client
        self.sabnzbd_client_factory = sabnzbd_client_factory or SABnzbdClient

    def initiate_download(self, media: Media, result: SearchResult) -> DownloadAttempt:
        content_type = ContentType.objects.get_for_model(media)

        active_attempts = DownloadAttempt.objects.filter(
            content_type=content_type,
            object_id=media.id,
            status__in=[
                DownloadAttemptStatus.SENT,
                DownloadAttemptStatus.DOWNLOADING,
            ],
        )

        if active_attempts.exists():
            raise DownloadServiceError(
                "Media already has an active download. Please delete the existing download attempt first."
            )

        download_client_config = (
            DownloadClientConfiguration.objects.filter(
                enabled=True, client_type="sabnzbd"
            )
            .order_by("priority")
            .first()
        )

        if not download_client_config:
            raise DownloadServiceError("No enabled SABnzbd configuration found")

        attempt = DownloadAttempt.objects.create(
            content_type=content_type,
            object_id=media.id,
            indexer=result.indexer,
            indexer_id=str(result.indexer_id),
            release_title=result.title,
            download_url=result.download_url,
            file_size=result.size,
            seeders=result.seeders,
            leechers=result.peers,
            status=DownloadAttemptStatus.PENDING,
            download_client=download_client_config,
        )

        try:
            download_response = self.prowlarr_client.send_to_download_client(
                indexer_id=result.indexer_id, guid=result.guid
            )

            attempt.status = DownloadAttemptStatus.SENT
            if download_response.get("download_client_id"):
                attempt.download_client_download_id = download_response[
                    "download_client_id"
                ]
            attempt.save()

            media.status = MediaStatus.DOWNLOADING
            media.save(update_fields=["status"])

            return attempt
        except Exception as e:
            attempt.status = DownloadAttemptStatus.FAILED
            attempt.error_type = "prowlarr_error"
            attempt.error_reason = str(e)
            attempt.save()
            raise DownloadServiceError(f"Failed to initiate download: {str(e)}")

    def get_download_status(self, attempt_id: UUID) -> DownloadAttempt:
        try:
            attempt = DownloadAttempt.objects.select_related("download_client").get(
                id=attempt_id
            )
        except DownloadAttempt.DoesNotExist:
            raise DownloadServiceError(f"Download attempt {attempt_id} not found")

        if not attempt.download_client:
            return attempt

        try:
            sabnzbd_client = self.sabnzbd_client_factory(attempt.download_client)
            job_status = sabnzbd_client.get_job_status(
                attempt.download_client_download_id
            )

            if not job_status:
                if attempt.status in [
                    DownloadAttemptStatus.SENT,
                    DownloadAttemptStatus.DOWNLOADING,
                ]:
                    attempt.status = DownloadAttemptStatus.FAILED
                    attempt.error_type = "not_found"
                    attempt.error_reason = (
                        "Download not found in SABnzbd queue or history"
                    )
                    attempt.save()
                return attempt

            if job_status.status == "Completed":
                if attempt.status != DownloadAttemptStatus.DOWNLOADED:
                    attempt.status = DownloadAttemptStatus.DOWNLOADED
                    if job_status.path:
                        attempt.raw_file_path = job_status.path
                    attempt.save()

                    media = attempt.media
                    if media:
                        media.status = MediaStatus.DOWNLOADED
                        media.save(update_fields=["status"])

            elif job_status.status in ["Downloading", "Queued", "Paused"]:
                if attempt.status != DownloadAttemptStatus.DOWNLOADING:
                    attempt.status = DownloadAttemptStatus.DOWNLOADING
                    attempt.save()

                    media = attempt.media
                    if media and media.status != MediaStatus.DOWNLOADING:
                        media.status = MediaStatus.DOWNLOADING
                        media.save(update_fields=["status"])

            elif job_status.status in ["Failed", "Deleted"]:
                if attempt.status != DownloadAttemptStatus.FAILED:
                    attempt.status = DownloadAttemptStatus.FAILED
                    attempt.error_type = "download_failed"
                    attempt.error_reason = f"SABnzbd status: {job_status.status}"
                    attempt.save()

        except Exception as e:
            attempt.error_type = "status_check_error"
            attempt.error_reason = str(e)
            attempt.save()

        return attempt

    def mark_as_blacklisted(
        self,
        attempt_id: UUID,
        reason: str = BlacklistReason.MANUAL,
        reason_details: str = "",
    ) -> None:
        try:
            attempt = DownloadAttempt.objects.select_related("download_client").get(
                id=attempt_id
            )
        except DownloadAttempt.DoesNotExist:
            raise DownloadServiceError(f"Download attempt {attempt_id} not found")

        content_type = ContentType.objects.get_for_model(attempt.media)

        DownloadBlacklist.objects.get_or_create(
            content_type=content_type,
            object_id=attempt.object_id,
            indexer=attempt.indexer,
            indexer_id=attempt.indexer_id,
            defaults={
                "release_title": attempt.release_title,
                "download_url": attempt.download_url,
                "reason": reason,
                "reason_details": reason_details,
            },
        )

        attempt.status = DownloadAttemptStatus.BLACKLISTED
        attempt.save()

    def delete_download_attempt(self, attempt_id: UUID) -> dict:
        try:
            attempt = DownloadAttempt.objects.select_related("download_client").get(
                id=attempt_id
            )
        except DownloadAttempt.DoesNotExist:
            raise DownloadServiceError(f"Download attempt {attempt_id} not found")

        messages = []
        was_active_download = False

        if attempt.status in [
            DownloadAttemptStatus.SENT,
            DownloadAttemptStatus.DOWNLOADING,
        ]:
            was_active_download = True

            if attempt.download_client and attempt.download_client_download_id:
                try:
                    sabnzbd_client = self.sabnzbd_client_factory(
                        attempt.download_client
                    )
                    deleted = sabnzbd_client.delete_job(
                        attempt.download_client_download_id
                    )
                    if deleted:
                        messages.append("Download removed from SABnzbd")
                    else:
                        messages.append(
                            "Warning: Could not remove download from SABnzbd"
                        )
                except Exception as e:
                    messages.append(
                        f"Warning: Error removing download from SABnzbd: {str(e)}"
                    )

        if attempt.raw_file_path:
            try:
                if os.path.isfile(attempt.raw_file_path):
                    os.remove(attempt.raw_file_path)
                    messages.append("Raw file deleted")
            except Exception as e:
                messages.append(f"Warning: Could not delete raw file: {str(e)}")

        if attempt.post_processed_file_path:
            try:
                if os.path.isfile(attempt.post_processed_file_path):
                    os.remove(attempt.post_processed_file_path)
                    messages.append("Post-processed file deleted")
            except Exception as e:
                messages.append(
                    f"Warning: Could not delete post-processed file: {str(e)}"
                )

        media = attempt.media
        attempt.delete()

        if was_active_download and media:
            has_other_downloads = DownloadAttempt.objects.filter(
                content_type=ContentType.objects.get_for_model(media),
                object_id=media.id,
                status__in=[
                    DownloadAttemptStatus.DOWNLOADED,
                    DownloadAttemptStatus.DOWNLOADING,
                    DownloadAttemptStatus.SENT,
                ],
            ).exists()

            if not has_other_downloads:
                media.status = MediaStatus.WANTED
                media.save(update_fields=["status"])
                messages.append("Media status reset to WANTED")

        return {"success": True, "messages": messages}
