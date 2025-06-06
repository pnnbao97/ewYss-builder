"""
Native File System Skill for PDFToSlidesConverter

This module provides file system operations for the PDF to Academic Slides Converter.
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional


class FileSystemSkill:
    """
    Skill for file system operations.
    """
    
    async def save_to_file(self, content: str, file_path: str) -> bool:
        """
        Save content to a file asynchronously.
        
        Args:
            content: Content to save
            file_path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Use run_in_executor to make file I/O non-blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_to_file_sync, content, file_path)
            
            return True
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            return False
    
    def _save_to_file_sync(self, content: str, file_path: str) -> None:
        """
        Synchronous function to save content to a file.
        
        Args:
            content: Content to save
            file_path: Path to the file
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    async def read_from_file(self, file_path: str) -> Optional[str]:
        """
        Read content from a file asynchronously.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string, or None if file doesn't exist or error occurs
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            # Use run_in_executor to make file I/O non-blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._read_from_file_sync, file_path)
            
            return content
        except Exception as e:
            print(f"Error reading from file: {str(e)}")
            return None
    
    def _read_from_file_sync(self, file_path: str) -> str:
        """
        Synchronous function to read content from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    async def list_files(self, directory: str, extension: Optional[str] = None) -> List[str]:
        """
        List files in a directory asynchronously.
        
        Args:
            directory: Directory to list files from
            extension: Optional file extension filter
            
        Returns:
            List of file paths
        """
        if not os.path.exists(directory):
            return []
        
        try:
            # Use run_in_executor to make file I/O non-blocking
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(None, self._list_files_sync, directory, extension)
            
            return files
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []
    
    def _list_files_sync(self, directory: str, extension: Optional[str] = None) -> List[str]:
        """
        Synchronous function to list files in a directory.
        
        Args:
            directory: Directory to list files from
            extension: Optional file extension filter
            
        Returns:
            List of file paths
        """
        files = []
        
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            
            if os.path.isfile(file_path):
                if extension is None or file.endswith(extension):
                    files.append(file_path)
        
        return files
    
    async def save_json(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        Save data as JSON to a file asynchronously.
        
        Args:
            data: Data to save
            file_path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert data to JSON
            json_str = json.dumps(data, indent=2)
            
            # Save to file
            return await self.save_to_file(json_str, file_path)
        except Exception as e:
            print(f"Error saving JSON: {str(e)}")
            return False
    
    async def load_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from a file asynchronously.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Loaded JSON data, or None if file doesn't exist or error occurs
        """
        content = await self.read_from_file(file_path)
        
        if content is None:
            return None
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {str(e)}")
            return None
