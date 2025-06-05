"""
Narration Skill for PDFToSlidesConverter

This module provides functionality to generate detailed narration scripts for slides.
Uses Gemini 2.5 Flash for narration generation tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class GenerateNarration:
    """
    Generates detailed narration scripts for slides.
    Uses Gemini 2.5 Flash for narration generation tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the narration generator skill with the specified model and API key.
        
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
            I need to create a detailed narration script for the following slide:

            Slide HTML: {{slide_html}}
            Slide Data: {{slide_data}}

            Please generate a comprehensive narration script (300-500 words) that explains this slide content in detail, including:
            - Introduction to the slide topic
            - Explanation of all key points
            - Context and background information
            - Connections to broader concepts
            - Conclusion or transition to the next slide
            
            The narration should be academic in tone but engaging, suitable for a lecture or presentation.
            """
    
    async def generate_narration(self, context: Dict[str, str]) -> str:
        """
        Generate a detailed narration script for a slide.
        
        Args:
            context: Dictionary containing slide HTML and slide data
            
        Returns:
            Narration script for the slide
            
        Raises:
            ValueError: If required data is missing from context
            RuntimeError: If narration generation fails
        """
        if "slide_html" not in context:
            raise ValueError("Slide HTML is missing from context")
        
        if "slide_data" not in context:
            raise ValueError("Slide data is missing from context")
        
        slide_html = context["slide_html"]
        slide_data = context["slide_data"]
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template
        prompt = prompt.replace("{{slide_html}}", slide_html)
        prompt = prompt.replace("{{slide_data}}", slide_data)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.7,  # Higher temperature for more creative narration
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate narration
            response = model.generate_content(prompt)
            
            # Extract the narration
            narration = response.text.strip()
            
            return narration
            
        except Exception as e:
            raise RuntimeError(f"Narration generation failed: {str(e)}")
