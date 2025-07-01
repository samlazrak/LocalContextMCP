"""
Configuration management for MCP Server.
Uses environment variables for secure, flexible configuration.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """PostgreSQL database configuration."""
    
    host: str = Field(default="localhost", env="PGHOST")
    port: int = Field(default=5432, env="PGPORT")
    database: str = Field(default="mcp_server", env="PGDATABASE")
    user: str = Field(default="postgres", env="PGUSER")
    password: str = Field(default="postgres", env="PGPASSWORD")
    
    # Connection pool settings
    min_connections: int = Field(default=5, env="DB_MIN_CONNECTIONS")
    max_connections: int = Field(default=20, env="DB_MAX_CONNECTIONS")
    
    @property
    def url(self) -> str:
        """Return PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        """Return async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class LLMConfig(BaseSettings):
    """Large Language Model configuration."""
    
    # Default LLM provider (lmstudio, ollama, openai)
    default_provider: str = Field(default="lmstudio", env="LLM_DEFAULT_PROVIDER")
    
    # LM Studio settings
    lmstudio_base_url: str = Field(default="http://localhost:1234/v1", env="LMSTUDIO_BASE_URL")
    lmstudio_model: str = Field(default="", env="LMSTUDIO_MODEL")
    
    # Ollama settings
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="", env="OLLAMA_MODEL")
    
    # OpenAI settings (if using OpenAI)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    
    # General LLM settings
    max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    timeout: int = Field(default=60, env="LLM_TIMEOUT")


class ServerConfig(BaseSettings):
    """MCP Server configuration."""
    
    host: str = Field(default="0.0.0.0", env="MCP_HOST")
    port: int = Field(default=8080, env="MCP_PORT")
    workers: int = Field(default=1, env="MCP_WORKERS")
    
    # Security settings
    enable_cors: bool = Field(default=True, env="MCP_ENABLE_CORS")
    cors_origins: List[str] = Field(default=["*"], env="MCP_CORS_ORIGINS")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", env="MCP_API_PREFIX")
    enable_docs: bool = Field(default=True, env="MCP_ENABLE_DOCS")
    
    # Rate limiting
    enable_rate_limiting: bool = Field(default=False, env="MCP_ENABLE_RATE_LIMITING")
    rate_limit_requests: int = Field(default=100, env="MCP_RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="MCP_RATE_LIMIT_WINDOW")


class ToolsConfig(BaseSettings):
    """Tools configuration."""
    
    # File system tool settings
    fs_allowed_paths: List[str] = Field(default=["/workspace"], env="MCP_FS_ALLOWED_PATHS")
    fs_max_file_size: int = Field(default=10 * 1024 * 1024, env="MCP_FS_MAX_FILE_SIZE")  # 10MB
    
    # Git tool settings
    git_allowed_repos: List[str] = Field(default=[], env="MCP_GIT_ALLOWED_REPOS")
    
    # Web tool settings
    web_enable_fetch: bool = Field(default=True, env="MCP_WEB_ENABLE_FETCH")
    web_enable_search: bool = Field(default=True, env="MCP_WEB_ENABLE_SEARCH")
    web_max_response_size: int = Field(default=5 * 1024 * 1024, env="MCP_WEB_MAX_RESPONSE_SIZE")  # 5MB
    web_timeout: int = Field(default=30, env="MCP_WEB_TIMEOUT")
    
    # Code intelligence settings
    code_enable_completion: bool = Field(default=True, env="MCP_CODE_ENABLE_COMPLETION")
    code_enable_analysis: bool = Field(default=True, env="MCP_CODE_ENABLE_ANALYSIS")
    code_cache_timeout: int = Field(default=3600, env="MCP_CODE_CACHE_TIMEOUT")  # 1 hour


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    file_path: str = Field(default="logs/mcp_server.log", env="LOG_FILE_PATH")
    file_max_size: int = Field(default=100 * 1024 * 1024, env="LOG_FILE_MAX_SIZE")  # 100MB
    file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    
    @validator("level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    # Authentication settings
    enable_auth: bool = Field(default=False, env="MCP_ENABLE_AUTH")
    jwt_secret_key: Optional[str] = Field(default=None, env="MCP_JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="MCP_JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="MCP_JWT_EXPIRATION_HOURS")
    
    # Input validation
    max_request_size: int = Field(default=10 * 1024 * 1024, env="MCP_MAX_REQUEST_SIZE")  # 10MB
    enable_input_sanitization: bool = Field(default=True, env="MCP_ENABLE_INPUT_SANITIZATION")
    
    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret key if auth is enabled."""
        if values.get("enable_auth") and not v:
            raise ValueError("JWT secret key is required when authentication is enabled")
        return v


class Config(BaseSettings):
    """Main configuration class combining all settings."""
    
    # Environment settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Component configurations
    database: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    server: ServerConfig = ServerConfig()
    tools: ToolsConfig = ToolsConfig()
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v.lower()
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def setup_logging_directory(self) -> None:
        """Ensure logging directory exists."""
        if self.logging.file_enabled:
            log_dir = Path(self.logging.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config()

# Convenience function to get config
def get_config() -> Config:
    """Get the global configuration instance."""
    return config


# Initialize logging directory on import
config.setup_logging_directory()