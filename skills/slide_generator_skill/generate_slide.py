"""
Slide Generator Skill for PDFToSlidesConverter

This module provides functionality to generate HTML code for slides.
Uses Gemini 2.5 Flash for slide generation tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class GenerateSlide:
    """
    Generates HTML code for slides.
    Uses Gemini 2.5 Flash for slide generation tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the slide generator skill with the specified model and API key.
        
        Args:
            model: Gemini model to use (e.g., "gemini-2.5-flash")
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
            I need to generate HTML code for a slide with the following components:

            Slide Data: {{slide_data}}
            Theme and Layout: {{theme}}
            Visualization (if any): {{visualization}}
            Image URL (if any): {{image_url}}

            Please generate complete HTML code for this slide, including all necessary CSS and JavaScript.
            The HTML should be high-quality academic slide with smooth animations and professional design.
            Include appropriate icons for headings (like key icon for "Key Points" sections).
            Make sure the slide is responsive and visually appealing.
            """
    
    async def generate_slide(self, context: Dict[str, str]) -> str:
        """
        Generate HTML code for a slide.
        
        Args:
            context: Dictionary containing slide data, theme, visualization, and image URL
            
        Returns:
            HTML code for the slide
            
        Raises:
            ValueError: If required data is missing from context
            RuntimeError: If slide generation fails
        """
        if "slide_data" not in context:
            raise ValueError("Slide data is missing from context")
        
        if "theme" not in context:
            raise ValueError("Theme is missing from context")
        
        slide_data = context["slide_data"]
        theme = context["theme"]
        visualization = context.get("visualization", "")
        image_url = context.get("image_url", "")
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template
        prompt = prompt.replace("{{slide_data}}", slide_data)
        prompt = prompt.replace("{{theme}}", theme)
        prompt = prompt.replace("{{visualization}}", visualization)
        prompt = prompt.replace("{{image_url}}", image_url)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.4,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate slide HTML
            response = model.generate_content(prompt)
            
            # Extract the HTML code
            result = response.text
            
            # Try to extract HTML from the response
            import re
            html_match = re.search(r'```(?:html)?\s*([\s\S]*?)\s*```', result)
            
            if html_match:
                html_code = html_match.group(1).strip()
            else:
                # If no code block is found, use the entire response
                html_code = result.strip()
            
            # Ensure the HTML is valid and complete
            if not html_code.startswith("<"):
                html_code = f"<div class='slide'>\n{html_code}\n</div>"
            
            return html_code
            
        except Exception as e:
            raise RuntimeError(f"Slide generation failed: {str(e)}")
