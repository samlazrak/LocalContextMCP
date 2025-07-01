"""Tests for configuration management."""

import pytest
from unittest.mock import patch, MagicMock
import os


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        try:
            from src.core.config import Settings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        # Mock environment to avoid loading actual .env
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            assert settings.server.host == "0.0.0.0"
            assert settings.server.port == 8080
            assert settings.server.log_level == "INFO"
            assert settings.database.pool_size == 10
            assert settings.lmstudio.base_url == "http://localhost:1234/v1"

    def test_environment_override(self):
        """Test environment variable override."""
        try:
            from src.core.config import Settings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        test_env = {
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "LMSTUDIO_BASE_URL": "http://test:1234/v1"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
            
            assert settings.server.host == "127.0.0.1"
            assert settings.server.port == 9000
            assert settings.server.log_level == "DEBUG"
            assert settings.database.url == "postgresql://test:test@localhost/test"
            assert settings.lmstudio.base_url == "http://test:1234/v1"

    def test_invalid_log_level(self):
        """Test validation of log level."""
        try:
            from src.core.config import Settings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=True):
            with pytest.raises(ValueError):
                Settings()

    def test_environment_detection(self):
        """Test environment detection methods."""
        try:
            from src.core.config import Settings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            settings = Settings()
            assert settings.is_development() is True
            assert settings.is_production() is False
        
        # Test production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            settings = Settings()
            assert settings.is_development() is False
            assert settings.is_production() is True


class TestDatabaseSettings:
    """Test database settings."""

    def test_default_database_settings(self):
        """Test default database configuration."""
        try:
            from src.core.config import DatabaseSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        with patch.dict(os.environ, {}, clear=True):
            settings = DatabaseSettings()
            
            assert "postgresql://" in settings.url
            assert settings.pool_size == 10
            assert settings.max_overflow == 20
            assert settings.pool_timeout == 30

    def test_database_url_override(self):
        """Test database URL override."""
        try:
            from src.core.config import DatabaseSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        test_url = "postgresql://user:pass@host:5432/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}, clear=True):
            settings = DatabaseSettings()
            assert settings.url == test_url


class TestLMStudioSettings:
    """Test LM Studio settings."""

    def test_default_lmstudio_settings(self):
        """Test default LM Studio configuration."""
        try:
            from src.core.config import LMStudioSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        with patch.dict(os.environ, {}, clear=True):
            settings = LMStudioSettings()
            
            assert settings.base_url == "http://localhost:1234/v1"
            assert settings.model == "qwen2.5-coder-0.5B-instruct"
            assert settings.timeout == 30
            assert settings.max_tokens == 4096
            assert settings.temperature == 0.1

    def test_lmstudio_url_override(self):
        """Test LM Studio URL override."""
        try:
            from src.core.config import LMStudioSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        test_url = "http://remote-host:1234/v1"
        with patch.dict(os.environ, {"LMSTUDIO_BASE_URL": test_url}, clear=True):
            settings = LMStudioSettings()
            assert settings.base_url == test_url


class TestDeepSeekSettings:
    """Test DeepSeek settings."""

    def test_default_deepseek_settings(self):
        """Test default DeepSeek configuration."""
        try:
            from src.core.config import DeepSeekSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        with patch.dict(os.environ, {}, clear=True):
            settings = DeepSeekSettings()
            
            assert settings.base_url == "http://localhost:8000/v1"
            assert settings.model == "deepseek-coder"
            assert settings.api_key is None
            assert settings.timeout == 60

    def test_deepseek_api_key_override(self):
        """Test DeepSeek API key override."""
        try:
            from src.core.config import DeepSeekSettings
        except ImportError:
            pytest.skip("Dependencies not available")
        
        test_key = "test-api-key"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": test_key}, clear=True):
            settings = DeepSeekSettings()
            assert settings.api_key == test_key