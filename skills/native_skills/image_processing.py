"""
Image Processing Skill for PDFToSlidesConverter

This module provides functionality to process images,
including downloading, resizing, and analyzing images.
"""

import os
import asyncio
import aiohttp
from PIL import Image
from typing import Dict, Tuple, Optional
import io


class ImageProcessingSkill:
    """
    Provides methods to process images.
    Includes functionality for downloading, resizing, and analyzing images.
    """
    
    async def download_image(self, image_url: str, output_path: str) -> str:
        """
        Download an image from a URL.
        
        Args:
            image_url: URL of the image to download
            output_path: Path where to save the image
            
        Returns:
            Path to the downloaded image
            
        Raises:
            IOError: If download fails
        """
        # Create directory if it doesn't exist
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Download image
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise IOError(f"Failed to download image: HTTP {response.status}")
                    
                    image_data = await response.read()
                    
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
            
            return output_path
        except Exception as e:
            raise IOError(f"Failed to download image: {str(e)}")
    
    async def resize_image(self, image_path: str, width: int, height: int, output_path: str) -> str:
        """
        Resize an image.
        
        Args:
            image_path: Path to the image to resize
            width: Target width
            height: Target height
            output_path: Path where to save the resized image
            
        Returns:
            Path to the resized image
            
        Raises:
            FileNotFoundError: If the image does not exist
            IOError: If resizing fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Create directory if it doesn't exist
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        try:
            # Use PIL to resize image
            with Image.open(image_path) as img:
                resized_img = img.resize((width, height))
                resized_img.save(output_path)
            
            return output_path
        except Exception as e:
            raise IOError(f"Failed to resize image: {str(e)}")
    
    async def get_image_dimensions(self, image_path: str) -> Dict[str, int]:
        """
        Get the dimensions of an image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Dictionary with width and height
            
        Raises:
            FileNotFoundError: If the image does not exist
            IOError: If reading fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
            
            return {"width": width, "height": height}
        except Exception as e:
            raise IOError(f"Failed to get image dimensions: {str(e)}")
