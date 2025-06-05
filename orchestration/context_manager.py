"""
Context Manager for PDFToSlidesConverter

This module provides a context manager to store and retrieve results between different
agent operations in the PDF to slides conversion process.
"""

from typing import Dict, Any, Optional


class ContextManager:
    """
    Manages context and results between different agent operations.
    Provides storage and retrieval of intermediate results during the conversion process.
    """
    
    def __init__(self):
        """Initialize an empty result store."""
        self._result_store = {}
    
    def store_result(self, key: str, value: Any) -> None:
        """
        Store a result with the given key.
        
        Args:
            key: The key to store the result under
            value: The result value to store
        """
        self._result_store[key] = value
    
    def get_result(self, key: str) -> Any:
        """
        Get a result by key.
        
        Args:
            key: The key of the result to retrieve
            
        Returns:
            The stored result value
            
        Raises:
            KeyError: If the key is not found in the result store
        """
        if key in self._result_store:
            return self._result_store[key]
        
        raise KeyError(f"Result with key '{key}' not found in context manager.")
    
    def has_result(self, key: str) -> bool:
        """
        Check if a result with the given key exists.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in self._result_store
    
    def clear_results(self) -> None:
        """Clear all stored results."""
        self._result_store.clear()
    
    def get_all_keys(self) -> list:
        """
        Get all keys in the result store.
        
        Returns:
            A list of all keys in the result store
        """
        return list(self._result_store.keys())
