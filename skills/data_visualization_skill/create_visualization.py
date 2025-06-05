"""
Data Visualization Skill for PDFToSlidesConverter

This module provides functionality to create visualizations for data in slides.
Uses Gemini 2.0 Flash for data visualization tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class CreateVisualization:
    """
    Creates visualizations for data in slides.
    Uses Gemini 2.0 Flash for data visualization tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the data visualization skill with the specified model and API key.
        
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
            I need to create a visualization for the following data:

            Data: {{data}}
            Slide Context: {{slide_data}}

            Please generate JavaScript code using Chart.js to visualize this data appropriately.
            """
    
    async def create_visualization(self, context: Dict[str, str]) -> str:
        """
        Create a visualization for the data in the slide.
        
        Args:
            context: Dictionary containing the data and slide context
            
        Returns:
            JavaScript code for the visualization
            
        Raises:
            ValueError: If required data is missing from context
            RuntimeError: If visualization creation fails
        """
        if "data" not in context:
            raise ValueError("Data is missing from context")
        
        if "slide_data" not in context:
            raise ValueError("Slide data is missing from context")
        
        data = context["data"]
        slide_data = context["slide_data"]
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template.replace("{{data}}", data).replace("{{slide_data}}", slide_data)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate visualization code
            response = model.generate_content(prompt)
            
            # Extract the JavaScript code
            result = response.text
            
            # Clean up the result to extract just the JavaScript code
            import re
            js_code_match = re.search(r'```(?:javascript|js)?\s*([\s\S]*?)\s*```', result)
            
            if js_code_match:
                js_code = js_code_match.group(1).strip()
            else:
                # If no code block is found, use the entire response
                js_code = result.strip()
            
            return js_code
            
        except Exception as e:
            raise RuntimeError(f"Visualization creation failed: {str(e)}")
