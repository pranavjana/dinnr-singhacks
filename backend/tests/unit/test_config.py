"""Unit tests for Config class."""

import os
import pytest
from pathlib import Path

from mas_crawler.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_config_defaults(self):
        """Test that Config has correct default values."""
        config = Config()
        assert config.download_dir == "./downloads"
        assert config.request_timeout == 10
        assert config.pdf_timeout == 30
        assert config.max_pdf_size_mb == 50
        assert config.retry_max_attempts == 3
        assert "DINNR-AML-Crawler" in config.user_agent
        assert config.log_level == "INFO"

    def test_config_custom_values(self):
        """Test creating Config with custom values."""
        config = Config(
            download_dir="/custom/path",
            request_timeout=20,
            pdf_timeout=60,
            max_pdf_size_mb=100,
            retry_max_attempts=5,
            user_agent="CustomAgent/1.0",
            log_level="DEBUG",
        )
        assert config.download_dir == "/custom/path"
        assert config.request_timeout == 20
        assert config.pdf_timeout == 60
        assert config.max_pdf_size_mb == 100
        assert config.retry_max_attempts == 5
        assert config.user_agent == "CustomAgent/1.0"
        assert config.log_level == "DEBUG"

    def test_config_from_env_defaults(self, monkeypatch):
        """Test Config.from_env() with no environment variables set."""
        # Clear all relevant environment variables
        for key in [
            "MAS_DOWNLOAD_DIR",
            "MAS_REQUEST_TIMEOUT",
            "MAS_PDF_TIMEOUT",
            "MAS_MAX_PDF_SIZE_MB",
            "MAS_RETRY_ATTEMPTS",
            "MAS_USER_AGENT",
            "MAS_LOG_LEVEL",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = Config.from_env()
        assert config.download_dir == "./downloads"
        assert config.request_timeout == 10
        assert config.pdf_timeout == 30

    def test_config_from_env_with_overrides(self, monkeypatch):
        """Test Config.from_env() with environment variable overrides."""
        monkeypatch.setenv("MAS_DOWNLOAD_DIR", "/env/downloads")
        monkeypatch.setenv("MAS_REQUEST_TIMEOUT", "25")
        monkeypatch.setenv("MAS_PDF_TIMEOUT", "90")
        monkeypatch.setenv("MAS_MAX_PDF_SIZE_MB", "200")
        monkeypatch.setenv("MAS_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("MAS_USER_AGENT", "EnvAgent/2.0")
        monkeypatch.setenv("MAS_LOG_LEVEL", "WARNING")

        config = Config.from_env()
        assert config.download_dir == "/env/downloads"
        assert config.request_timeout == 25
        assert config.pdf_timeout == 90
        assert config.max_pdf_size_mb == 200
        assert config.retry_max_attempts == 5
        assert config.user_agent == "EnvAgent/2.0"
        assert config.log_level == "WARNING"

    def test_config_ensure_download_dir_creates_directory(self, tmp_path):
        """Test that ensure_download_dir() creates directory if it doesn't exist."""
        download_dir = tmp_path / "test_downloads"
        config = Config(download_dir=str(download_dir))

        # Directory should not exist yet
        assert not download_dir.exists()

        # Call ensure_download_dir
        config.ensure_download_dir()

        # Directory should now exist
        assert download_dir.exists()
        assert download_dir.is_dir()

    def test_config_ensure_download_dir_idempotent(self, tmp_path):
        """Test that ensure_download_dir() is idempotent (can be called multiple times)."""
        download_dir = tmp_path / "test_downloads"
        config = Config(download_dir=str(download_dir))

        # Call twice
        config.ensure_download_dir()
        config.ensure_download_dir()

        # Should still exist with no errors
        assert download_dir.exists()

    def test_config_to_dict(self):
        """Test that to_dict() returns correct dictionary representation."""
        config = Config(
            download_dir="/test",
            request_timeout=15,
            pdf_timeout=45,
            max_pdf_size_mb=75,
            retry_max_attempts=4,
            user_agent="TestAgent/1.0",
            log_level="ERROR",
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["download_dir"] == "/test"
        assert config_dict["request_timeout"] == 15
        assert config_dict["pdf_timeout"] == 45
        assert config_dict["max_pdf_size_mb"] == 75
        assert config_dict["retry_max_attempts"] == 4
        assert config_dict["user_agent"] == "TestAgent/1.0"
        assert config_dict["log_level"] == "ERROR"

    def test_config_partial_env_override(self, monkeypatch):
        """Test Config.from_env() with only some environment variables set."""
        # Set only some environment variables
        monkeypatch.setenv("MAS_DOWNLOAD_DIR", "/partial/path")
        monkeypatch.setenv("MAS_LOG_LEVEL", "DEBUG")

        config = Config.from_env()

        # Overridden values
        assert config.download_dir == "/partial/path"
        assert config.log_level == "DEBUG"

        # Default values for non-overridden settings
        assert config.request_timeout == 10
        assert config.pdf_timeout == 30
        assert config.max_pdf_size_mb == 50
