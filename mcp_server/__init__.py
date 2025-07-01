"""
MCP Server - A comprehensive Model Context Protocol server.
"""

__version__ = "1.0.0"
__author__ = "MCP Server Team"
__description__ = "A comprehensive Model Context Protocol server with LLM integration and tool support"

from .config import get_config
from .server import app

__all__ = ["get_config", "app"]