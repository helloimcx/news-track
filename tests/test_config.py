import os
import pytest
from app.config import Settings

def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    # Mock environment variables using the new delimiter
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SCHEDULER__TIMEZONE", "UTC") # Use double underscore for nested models
    
    # Create settings instance
    settings = Settings()
    
    # Assert values are loaded from env
    assert settings.app_name == "TestApp"
    assert settings.log_level == "DEBUG"
    assert settings.scheduler.timezone == "UTC"

def test_settings_defaults():
    """Test loading settings with defaults (no env vars)."""
    # Unset any potentially conflicting env vars for this test
    env_vars_to_unset = ["APP_NAME", "LOG_LEVEL", "SCHEDULER__TIMEZONE"]
    for var in env_vars_to_unset:
        if var in os.environ:
            del os.environ[var]
            
    # Create settings instance
    settings = Settings()
    
    # Assert default values
    assert settings.app_name == "NewsTracker"
    assert settings.log_level == "INFO"
    assert settings.scheduler.timezone == "Asia/Shanghai" # Default for scheduler

# Add more tests for nested models, validation, etc. as needed