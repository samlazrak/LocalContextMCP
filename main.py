#!/usr/bin/env python3
"""
Main entry point for MCP Server.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from mcp_server.config import get_config
from mcp_server.utils.logging import setup_logging, get_logger


def main():
    """Main entry point."""
    try:
        # Get configuration
        config = get_config()
        
        # Setup logging
        setup_logging(
            level=config.logging.level,
            format_type=config.logging.format,
            file_path=config.logging.file_path if config.logging.file_enabled else None,
            file_max_size=config.logging.file_max_size,
            file_backup_count=config.logging.file_backup_count
        )
        
        logger = get_logger(__name__)
        logger.info("Starting MCP Server", version="1.0.0", environment=config.environment)
        
        # Import and run server
        import uvicorn
        from mcp_server.server import app
        
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            workers=config.server.workers,
            reload=config.is_development(),
            log_level=config.logging.level.lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down MCP Server (KeyboardInterrupt)")
    except Exception as e:
        logger.error("Failed to start MCP Server", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()