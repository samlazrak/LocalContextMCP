#!/usr/bin/env python3
"""
Real-time File System Watcher for Incremental Code Indexing
Monitors code files for changes and updates the code intelligence database
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Set, Callable, Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
import time
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)

class CodeFileWatcher(FileSystemEventHandler):
    """File system event handler for code files"""
    
    def __init__(self, callback: Callable, debounce_time: float = 1.0):
        super().__init__()
        self.callback = callback
        self.debounce_time = debounce_time
        self.watched_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.go', '.rs', '.php', '.rb', '.kt', '.swift', '.scala', '.cs', '.vue'
        }
        self.pending_changes = defaultdict(float)  # file_path -> last_change_time
        self._debounce_task = None
        
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule_callback(event.src_path, 'modified')
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule_callback(event.src_path, 'created')
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule_callback(event.src_path, 'deleted')
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            if self._is_code_file(event.src_path):
                self._schedule_callback(event.src_path, 'deleted')
            if self._is_code_file(event.dest_path):
                self._schedule_callback(event.dest_path, 'created')
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file we should monitor"""
        return Path(file_path).suffix.lower() in self.watched_extensions
    
    def _schedule_callback(self, file_path: str, event_type: str):
        """Schedule callback with debouncing to avoid excessive calls"""
        current_time = time.time()
        self.pending_changes[file_path] = current_time
        
        # Cancel existing debounce task
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        
        # Schedule new debounce task
        self._debounce_task = asyncio.create_task(
            self._debounced_callback(file_path, event_type, current_time)
        )
    
    async def _debounced_callback(self, file_path: str, event_type: str, change_time: float):
        """Execute callback after debounce delay"""
        await asyncio.sleep(self.debounce_time)
        
        # Check if this is still the latest change for this file
        if self.pending_changes.get(file_path) == change_time:
            try:
                await self.callback(file_path, event_type)
            except Exception as e:
                logger.error(f"Error in file watcher callback for {file_path}: {e}")
            finally:
                # Clean up pending change
                if file_path in self.pending_changes:
                    del self.pending_changes[file_path]

class IncrementalIndexer:
    """Manages incremental indexing of code changes"""
    
    def __init__(self, code_intelligence, db_pool=None):
        self.code_intelligence = code_intelligence
        self.db_pool = db_pool
        self.file_hashes = {}  # file_path -> hash
        self.project_watchers = {}  # project_path -> Observer
        
    async def start_watching_project(self, project_path: str):
        """Start watching a project for file changes"""
        if project_path in self.project_watchers:
            logger.info(f"Already watching project: {project_path}")
            return
        
        if not os.path.exists(project_path):
            logger.error(f"Project path does not exist: {project_path}")
            return
        
        # Create file watcher with callback
        event_handler = CodeFileWatcher(
            callback=self._handle_file_change,
            debounce_time=1.0
        )
        
        # Create and start observer
        observer = Observer()
        observer.schedule(event_handler, project_path, recursive=True)
        observer.start()
        
        self.project_watchers[project_path] = observer
        logger.info(f"Started watching project: {project_path}")
        
        # Initial indexing of existing files
        await self._initial_index_project(project_path)
    
    async def stop_watching_project(self, project_path: str):
        """Stop watching a project"""
        if project_path in self.project_watchers:
            observer = self.project_watchers[project_path]
            observer.stop()
            observer.join()
            del self.project_watchers[project_path]
            logger.info(f"Stopped watching project: {project_path}")
    
    async def stop_all_watchers(self):
        """Stop all project watchers"""
        for project_path in list(self.project_watchers.keys()):
            await self.stop_watching_project(project_path)
    
    async def _initial_index_project(self, project_path: str):
        """Perform initial indexing of all files in project"""
        logger.info(f"Starting initial indexing of project: {project_path}")
        
        indexed_count = 0
        for root, dirs, files in os.walk(project_path):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', '__pycache__', 'node_modules', '.venv', 'venv', 
                '.idea', '.vscode', 'dist', 'build', 'target'
            }]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self._should_index_file(file_path):
                    await self._handle_file_change(file_path, 'created')
                    indexed_count += 1
        
        logger.info(f"Initial indexing complete: {indexed_count} files indexed")
    
    async def _handle_file_change(self, file_path: str, event_type: str):
        """Handle individual file change events"""
        try:
            if event_type == 'deleted':
                await self._handle_file_deletion(file_path)
            else:
                await self._handle_file_update(file_path, event_type)
        except Exception as e:
            logger.error(f"Error handling file change {file_path} ({event_type}): {e}")
    
    async def _handle_file_update(self, file_path: str, event_type: str):
        """Handle file creation or modification"""
        if not os.path.exists(file_path):
            logger.warning(f"File no longer exists: {file_path}")
            return
        
        # Check if file has actually changed
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Skip if file hasn't actually changed
            if file_path in self.file_hashes and self.file_hashes[file_path] == file_hash:
                return
            
            # Update hash cache
            self.file_hashes[file_path] = file_hash
            
            # Invalidate old analysis cache
            self.code_intelligence.invalidate_file_cache(file_path)
            
            # Re-analyze file
            analysis = self.code_intelligence.analyze_file(file_path)
            
            if "error" not in analysis:
                logger.info(f"Re-indexed file: {file_path} ({analysis['symbol_count']} symbols)")
                
                # Update database if available
                if self.db_pool:
                    await self._update_database(file_path, analysis)
            else:
                logger.warning(f"Failed to analyze file {file_path}: {analysis['error']}")
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
    
    async def _handle_file_deletion(self, file_path: str):
        """Handle file deletion"""
        # Remove from caches
        if file_path in self.file_hashes:
            del self.file_hashes[file_path]
        
        self.code_intelligence.invalidate_file_cache(file_path)
        
        # Remove from database if available
        if self.db_pool:
            await self._remove_from_database(file_path)
        
        logger.info(f"Removed deleted file from index: {file_path}")
    
    async def _update_database(self, file_path: str, analysis: Dict[str, Any]):
        """Update database with file analysis"""
        try:
            async with self.db_pool.acquire() as conn:
                # Remove old symbols for this file
                await conn.execute(
                    "DELETE FROM code_symbols WHERE file_path = $1",
                    file_path
                )
                
                # Insert new symbols
                for symbol in analysis['symbols']:
                    await conn.execute("""
                        INSERT INTO code_symbols 
                        (file_path, symbol_name, symbol_type, line_start, line_end, 
                         column_start, column_end, signature, docstring, parent, scope, language)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """, 
                        file_path, symbol['name'], symbol['type'], symbol['line_start'],
                        symbol['line_end'], symbol['column_start'], symbol['column_end'],
                        symbol['signature'], symbol['docstring'], symbol['parent'],
                        symbol['scope'], symbol['language']
                    )
                
                logger.debug(f"Updated database for file: {file_path}")
                
        except Exception as e:
            logger.error(f"Database update failed for {file_path}: {e}")
    
    async def _remove_from_database(self, file_path: str):
        """Remove file data from database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM code_symbols WHERE file_path = $1",
                    file_path
                )
                await conn.execute(
                    "DELETE FROM file_dependencies WHERE source_file = $1",
                    file_path
                )
                logger.debug(f"Removed file from database: {file_path}")
                
        except Exception as e:
            logger.error(f"Database removal failed for {file_path}: {e}")
    
    def _should_index_file(self, file_path: str) -> bool:
        """Check if file should be indexed"""
        if not os.path.isfile(file_path):
            return False
        
        # Check extension
        ext = Path(file_path).suffix.lower()
        if ext not in {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h'}:
            return False
        
        # Skip large files (> 1MB)
        try:
            if os.path.getsize(file_path) > 1024 * 1024:
                return False
        except OSError:
            return False
        
        return True
    
    def get_watch_status(self) -> Dict[str, Any]:
        """Get status of all watchers"""
        return {
            "watched_projects": list(self.project_watchers.keys()),
            "total_watchers": len(self.project_watchers),
            "cached_files": len(self.file_hashes)
        }

class ProjectManager:
    """Manages multiple projects with file watching"""
    
    def __init__(self, code_intelligence, db_pool=None):
        self.indexer = IncrementalIndexer(code_intelligence, db_pool)
        self.active_projects = {}  # project_path -> project_info
    
    async def add_project(self, project_path: str, project_name: str = None) -> Dict[str, Any]:
        """Add a project for monitoring"""
        project_path = os.path.abspath(project_path)
        
        if not os.path.exists(project_path):
            return {"error": f"Project path does not exist: {project_path}"}
        
        if project_path in self.active_projects:
            return {"error": f"Project already being monitored: {project_path}"}
        
        # Start watching
        await self.indexer.start_watching_project(project_path)
        
        # Store project info
        project_info = {
            "name": project_name or os.path.basename(project_path),
            "path": project_path,
            "added_at": time.time(),
            "status": "active"
        }
        
        self.active_projects[project_path] = project_info
        
        return {
            "message": f"Successfully added project: {project_info['name']}",
            "project_info": project_info
        }
    
    async def remove_project(self, project_path: str) -> Dict[str, Any]:
        """Remove a project from monitoring"""
        project_path = os.path.abspath(project_path)
        
        if project_path not in self.active_projects:
            return {"error": f"Project not being monitored: {project_path}"}
        
        # Stop watching
        await self.indexer.stop_watching_project(project_path)
        
        # Remove from active projects
        project_info = self.active_projects.pop(project_path)
        
        return {
            "message": f"Successfully removed project: {project_info['name']}",
            "project_info": project_info
        }
    
    async def list_projects(self) -> Dict[str, Any]:
        """List all monitored projects"""
        return {
            "active_projects": list(self.active_projects.values()),
            "watch_status": self.indexer.get_watch_status()
        }
    
    async def shutdown(self):
        """Shutdown all project monitoring"""
        await self.indexer.stop_all_watchers()
        self.active_projects.clear()

# Global instance (to be initialized by main application)
project_manager = None 