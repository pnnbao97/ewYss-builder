"""
Theme Layout Skill for PDFToSlidesConverter

This module provides functionality to select appropriate themes and layouts for slides.
Uses Gemini 2.0 Flash for theme and layout selection tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class GetThemeAndLayout:
    """
    Selects appropriate themes and layouts for slides.
    Uses Gemini 2.0 Flash for theme and layout selection tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the theme and layout skill with the specified model and API key.
        
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
            I need to select an appropriate theme and layout for the following slide:

            Slide Data: {{slide_data}}

            Please provide a theme and layout configuration that best suits this slide content, including:
            - Theme name and color scheme
            - Layout structure
            - CSS classes and styling
            - Recommendations for visual elements
            """
    
    async def get_theme_and_layout(self, context: Dict[str, str]) -> str:
        """
        Select an appropriate theme and layout for the slide.
        
        Args:
            context: Dictionary containing the slide data
            
        Returns:
            JSON string with theme and layout configuration
            
        Raises:
            ValueError: If slide data is missing from context
            RuntimeError: If theme and layout selection fails
        """
        if "slide_data" not in context:
            raise ValueError("Slide data is missing from context")
        
        slide_data = context["slide_data"]
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template.replace("{{slide_data}}", slide_data)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate theme and layout configuration
            response = model.generate_content(prompt)
            
            # Extract the theme and layout configuration
            result = response.text
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result)
            
            if json_match:
                json_str = json_match.group(1).strip()
                try:
                    # Validate JSON
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    pass
            
            # If no valid JSON found, create a structured JSON from the text
            theme_match = re.search(r'Theme(?:\s+name)?[:\s]+([\w\s-]+)', result, re.IGNORECASE)
            color_match = re.search(r'Color(?:\s+scheme)?[:\s]+([\w\s-]+)', result, re.IGNORECASE)
            layout_match = re.search(r'Layout(?:\s+structure)?[:\s]+([\w\s-]+)', result, re.IGNORECASE)
            
            theme_config = {
                "themeName": theme_match.group(1).strip() if theme_match else "academic",
                "colorScheme": color_match.group(1).strip() if color_match else "blue",
                "layout": layout_match.group(1).strip() if layout_match else "title-content",
                "cssClasses": "slide-academic"
            }
            
            return json.dumps(theme_config)
            
        except Exception as e:
            raise RuntimeError(f"Theme and layout selection failed: {str(e)}")
