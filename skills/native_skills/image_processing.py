"""
Image Processing Skill for PDFToSlidesConverter

This module provides image processing operations for the PDF to Academic Slides Converter.
"""

import os
import asyncio
from typing import List, Optional, Tuple
from PIL import Image, ImageOps, ImageEnhance


class ImageProcessingSkill:
    """
    Skill for image processing operations.
    """
    
    async def optimize_image(self, image_path: str, output_path: Optional[str] = None, 
                            max_size: Tuple[int, int] = (1200, 800), quality: int = 85) -> str:
        """
        Optimize an image for presentation use asynchronously.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the optimized image (if None, overwrites the original)
            max_size: Maximum dimensions (width, height) for the image
            quality: JPEG quality (1-100)
            
        Returns:
            Path to the optimized image
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if output_path is None:
            output_path = image_path
        
        # Use run_in_executor to make image processing non-blocking
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None, self._optimize_image_sync, image_path, output_path, max_size, quality
        )
        
        return result_path
    
    def _optimize_image_sync(self, image_path: str, output_path: str, 
                           max_size: Tuple[int, int], quality: int) -> str:
        """
        Synchronous function to optimize an image for presentation use.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the optimized image
            max_size: Maximum dimensions (width, height) for the image
            quality: JPEG quality (1-100)
            
        Returns:
            Path to the optimized image
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Open the image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Save the optimized image
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
        
        return output_path
    
    async def crop_image(self, image_path: str, output_path: str, 
                       crop_box: Tuple[int, int, int, int]) -> str:
        """
        Crop an image asynchronously.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the cropped image
            crop_box: Crop box (left, top, right, bottom)
            
        Returns:
            Path to the cropped image
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Use run_in_executor to make image processing non-blocking
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None, self._crop_image_sync, image_path, output_path, crop_box
        )
        
        return result_path
    
    def _crop_image_sync(self, image_path: str, output_path: str, 
                       crop_box: Tuple[int, int, int, int]) -> str:
        """
        Synchronous function to crop an image.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the cropped image
            crop_box: Crop box (left, top, right, bottom)
            
        Returns:
            Path to the cropped image
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Open the image
        with Image.open(image_path) as img:
            # Crop the image
            cropped_img = img.crop(crop_box)
            
            # Save the cropped image
            cropped_img.save(output_path)
        
        return output_path
    
    async def enhance_image(self, image_path: str, output_path: str, 
                          brightness: float = 1.0, contrast: float = 1.0, 
                          sharpness: float = 1.0) -> str:
        """
        Enhance an image asynchronously.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the enhanced image
            brightness: Brightness factor (1.0 = original)
            contrast: Contrast factor (1.0 = original)
            sharpness: Sharpness factor (1.0 = original)
            
        Returns:
            Path to the enhanced image
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Use run_in_executor to make image processing non-blocking
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None, self._enhance_image_sync, image_path, output_path, 
            brightness, contrast, sharpness
        )
        
        return result_path
    
    def _enhance_image_sync(self, image_path: str, output_path: str, 
                          brightness: float, contrast: float, sharpness: float) -> str:
        """
        Synchronous function to enhance an image.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the enhanced image
            brightness: Brightness factor (1.0 = original)
            contrast: Contrast factor (1.0 = original)
            sharpness: Sharpness factor (1.0 = original)
            
        Returns:
            Path to the enhanced image
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Open the image
        with Image.open(image_path) as img:
            # Apply enhancements
            if brightness != 1.0:
                img = ImageEnhance.Brightness(img).enhance(brightness)
            
            if contrast != 1.0:
                img = ImageEnhance.Contrast(img).enhance(contrast)
            
            if sharpness != 1.0:
                img = ImageEnhance.Sharpness(img).enhance(sharpness)
            
            # Save the enhanced image
            img.save(output_path)
        
        return output_path
    
    async def process_images_in_parallel(self, image_paths: List[str], 
                                       output_dir: str, max_size: Tuple[int, int] = (1200, 800), 
                                       quality: int = 85, max_concurrent: int = 5) -> List[str]:
        """
        Process multiple images in parallel asynchronously.
        
        Args:
            image_paths: List of paths to input images
            output_dir: Directory to save processed images
            max_size: Maximum dimensions (width, height) for the images
            quality: JPEG quality (1-100)
            max_concurrent: Maximum number of concurrent image processing tasks
            
        Returns:
            List of paths to processed images
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_image(image_path: str) -> str:
            """Process a single image with semaphore control."""
            async with semaphore:
                # Generate output path
                filename = os.path.basename(image_path)
                output_path = os.path.join(output_dir, filename)
                
                # Optimize the image
                return await self.optimize_image(image_path, output_path, max_size, quality)
        
        # Process images in parallel
        tasks = [process_image(path) for path in image_paths]
        result_paths = await asyncio.gather(*tasks)
        
        return result_paths
