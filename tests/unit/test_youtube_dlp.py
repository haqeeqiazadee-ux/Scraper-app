import pytest
from packages.connectors.youtube_dlp_connector import YoutubeDlpConnector
from unittest.mock import MagicMock, patch

@pytest.fixture
def connector():
    return YoutubeDlpConnector()

def test_extract_metadata_success(connector):
    mock_info = {
        "id": "123",
        "title": "Test Video",
        "uploader": "Test Channel",
        "view_count": 1000
    }

    with patch("packages.connectors.youtube_dlp_connector.yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = mock_info

        result = connector.extract_metadata("https://youtube.com/watch?v=123")
        assert result["id"] == "123"
        assert result["title"] == "Test Video"
        assert result["uploader"] == "Test Channel"
        assert result["view_count"] == 1000

def test_extract_metadata_failure(connector):
    with patch("packages.connectors.youtube_dlp_connector.yt_dlp.YoutubeDL") as mock_ydl:
        mock_instance = mock_ydl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("Failed")

        result = connector.extract_metadata("https://youtube.com/watch?v=error")
        assert "error" in result
        assert "Failed" in result["error"]
