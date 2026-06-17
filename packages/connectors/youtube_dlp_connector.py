"""
yt-dlp Connector for video metadata extraction and downloading.
"""

from __future__ import annotations

import logging
from typing import Any

import yt_dlp

logger = logging.getLogger(__name__)

class YoutubeDlpConnector:
    """Extracts metadata and media from YouTube and other video platforms."""

    def __init__(self, download_audio: bool = False, download_video: bool = False) -> None:
        self.download_audio = download_audio
        self.download_video = download_video
        self.ydl_opts: dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': not (download_audio or download_video),
            'skip_download': not (download_audio or download_video),
        }

        if download_audio:
            self.ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif download_video:
            self.ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
            })

    def extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract metadata from a video URL without downloading the file."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}

                return {
                    "id": info.get("id"),
                    "title": info.get("title"),
                    "description": info.get("description"),
                    "uploader": info.get("uploader"),
                    "uploader_id": info.get("uploader_id"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "duration": info.get("duration"),
                    "upload_date": info.get("upload_date"),
                    "channel_url": info.get("channel_url"),
                    "thumbnail": info.get("thumbnail"),
                    "tags": info.get("tags", []),
                }
        except Exception as e:
            logger.error("Failed to extract video metadata for %s: %s", url, e)
            return {"error": str(e)}

    def extract_transcript(self, url: str) -> dict[str, Any]:
        """Extract available subtitles/transcripts if available."""
        opts = self.ydl_opts.copy()
        opts.update({
            'writesubtitles': True,
            'allsubtitles': True,
            'skip_download': True,
        })
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "subtitles": info.get("subtitles", {}),
                    "automatic_captions": info.get("automatic_captions", {})
                }
        except Exception as e:
            logger.error("Failed to extract transcript for %s: %s", url, e)
            return {"error": str(e)}
