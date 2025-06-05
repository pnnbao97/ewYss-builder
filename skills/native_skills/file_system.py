"""
File System Skill for PDFToSlidesConverter

This module provides functionality to interact with the file system,
including saving and reading files, and listing directory contents.
"""

import os
import asyncio
from typing import List, Optional


class FileSystemSkill:
    """
    Provides methods to interact with the file system.
    Includes functionality for saving and reading files, and listing directory contents.
    """
    
    async def save_to_file(self, content: str, file_path: str) -> str:
        """
        Save content to a file.
        
        Args:
            content: Content to save
            file_path: Path where to save the content
            
        Returns:
            Message indicating success
            
        Raises:
            IOError: If saving fails
        """
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Write content to file
        try:
            async with asyncio.Lock():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return f"Content saved to {file_path}"
        except IOError as e:
            raise IOError(f"Failed to save file: {str(e)}")
    
    async def read_from_file(self, file_path: str) -> str:
        """
        Read content from a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content
            
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If reading fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            async with asyncio.Lock():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except IOError as e:
            raise IOError(f"Failed to read file: {str(e)}")
    
    async def list_files(self, directory_path: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory.
        
        Args:
            directory_path: Path to the directory
            pattern: Optional file pattern to filter (e.g., "*.html")
            
        Returns:
            List of file paths
            
        Raises:
            NotADirectoryError: If the directory does not exist
        """
        if not os.path.exists(directory_path):
            raise NotADirectoryError(f"Directory not found: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Not a directory: {directory_path}")
        
        import glob
        
        if pattern:
            return glob.glob(os.path.join(directory_path, pattern))
        else:
            return [os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                   if os.path.isfile(os.path.join(directory_path, f))]
