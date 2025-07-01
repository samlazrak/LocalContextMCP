"""Configuration management for LocalContextMCP."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/localcontextmcp",
        description="Database connection URL"
    )
    pool_size: int = Field(default=10, description="Database connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, description="Pool connection timeout")
    
    class Config:
        env_prefix = "DATABASE_"


class LMStudioSettings(BaseSettings):
    """LM Studio configuration settings."""
    
    base_url: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio API base URL"
    )
    model: str = Field(
        default="qwen2.5-coder-0.5B-instruct",
        description="Default model for completions"
    )
    embedding_model: str = Field(
        default="qwen2.5-coder-0.5B-instruct",
        description="Model for embeddings"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_tokens: int = Field(default=4096, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, description="Model temperature")
    
    class Config:
        env_prefix = "LMSTUDIO_"


class DeepSeekSettings(BaseSettings):
    """DeepSeek configuration settings."""
    
    base_url: Optional[str] = Field(
        default="http://localhost:8000/v1",
        description="DeepSeek API base URL"
    )
    model: str = Field(
        default="deepseek-coder",
        description="DeepSeek model name"
    )
    api_key: Optional[str] = Field(default=None, description="DeepSeek API key")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    
    class Config:
        env_prefix = "DEEPSEEK_"


class ServerSettings(BaseSettings):
    """Server configuration settings."""
    
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for sessions"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts"
    )
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        env_prefix = ""


class ProjectSettings(BaseSettings):
    """Project and file handling settings."""
    
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    max_project_files: int = Field(
        default=10000,
        description="Maximum files to analyze in a project"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    supported_languages: List[str] = Field(
        default=[
            "python", "javascript", "typescript", "java", "cpp", "c",
            "go", "rust", "php", "ruby", "swift", "kotlin", "scala"
        ],
        description="Supported programming languages"
    )
    
    class Config:
        env_prefix = ""


class MonitoringSettings(BaseSettings):
    """Monitoring and metrics settings."""
    
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    health_check_interval: int = Field(
        default=60,
        description="Health check interval in seconds"
    )
    
    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main application settings."""
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    lmstudio: LMStudioSettings = Field(default_factory=LMStudioSettings)
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment and .env file."""
        return cls()
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev")
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")


# Global settings instance
settings = Settings.load()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings