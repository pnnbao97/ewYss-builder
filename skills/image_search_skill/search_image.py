"""
Image Search Skill for PDFToSlidesConverter

This module provides functionality to search for appropriate images for slides.
Uses Gemini 2.0 Flash for image search tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai
import aiohttp


class SearchImage:
    """
    Searches for appropriate images for slides.
    Uses Gemini 2.0 Flash for image search tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the image search skill with the specified model and API key.
        
        Args:
            model: Gemini model to use (e.g., "gemini-2.0-flash")
            api_key: Gemini API key
        """
        self.model = model
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """
        Load the prompt template from the skill directory.
        
        Returns:
            The prompt template as a string
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct the path to the prompt template
        prompt_path = os.path.join(current_dir, "prompt.txt")
        
        # Load the prompt template
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            # Return a default prompt if the file doesn't exist
            return """
            I need to find an appropriate image for the following slide content:

            Slide Data: {{slide_data}}
            Image Keywords: {{image_keywords}}

            Please search for and return the URL of an image that best illustrates this slide content.
            """
    
    async def search_image(self, context: Dict[str, str]) -> str:
        """
        Search for an appropriate image for the slide.
        
        Args:
            context: Dictionary containing the slide data and image keywords
            
        Returns:
            URL of the found image
            
        Raises:
            ValueError: If required data is missing from context
            RuntimeError: If image search fails
        """
        if "slide_data" not in context:
            raise ValueError("Slide data is missing from context")
        
        if "image_keywords" not in context:
            raise ValueError("Image keywords are missing from context")
        
        slide_data = context["slide_data"]
        image_keywords = context["image_keywords"]
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template.replace("{{slide_data}}", slide_data).replace("{{image_keywords}}", image_keywords)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate image search query
            response = model.generate_content(prompt)
            
            # Extract the search query
            search_query = response.text.strip()
            
            # Use the search query to find an image
            image_url = await self._search_image_api(search_query)
            
            return image_url
            
        except Exception as e:
            raise RuntimeError(f"Image search failed: {str(e)}")
    
    async def _search_image_api(self, query: str) -> str:
        """
        Search for an image using an image search API.
        
        Args:
            query: Search query
            
        Returns:
            URL of the found image
            
        Raises:
            RuntimeError: If image search fails
        """
        # This is a simplified implementation
        # In a real-world scenario, you would use a proper image search API
        
        # For demonstration purposes, we'll use a placeholder image URL based on the query
        # In a real implementation, you would use Unsplash API, Pexels API, or similar
        
        try:
            # Sanitize the query for URL
            import urllib.parse
            sanitized_query = urllib.parse.quote(query)
            
            # Try to use Unsplash API if available
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://source.unsplash.com/featured/?{sanitized_query}") as response:
                        if response.status == 200:
                            return str(response.url)
            except:
                pass
            
            # Fallback to placeholder image
            return f"https://via.placeholder.com/800x600?text={sanitized_query}"
            
        except Exception as e:
            raise RuntimeError(f"Image API search failed: {str(e)}")
