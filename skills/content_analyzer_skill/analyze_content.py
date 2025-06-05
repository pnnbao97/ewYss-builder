"""
Content Analyzer Skill for PDFToSlidesConverter

This module provides functionality to analyze PDF content and segment it into logical slides.
Uses Gemini 2.5 Pro for complex content analysis.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class AnalyzeContent:
    """
    Analyzes PDF content and segments it into logical slides.
    Uses Gemini 2.5 Pro for complex content analysis.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the content analyzer with the specified model and API key.
        
        Args:
            model: Gemini model to use (e.g., "gemini-2.5-pro")
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
            I need to analyze the following PDF content and segment it into logical slides:

            PDF Content: {{pdf_content}}

            Please analyze this content and return a structured JSON array of slide data, where each slide includes:
            - SlideNumber
            - Title
            - Content (array of points)
            - HasData (boolean indicating if the slide contains data that needs visualization)
            - Data (string representation of data if HasData is true)
            - NeedsImage (boolean indicating if the slide needs an illustrative image)
            - ImageKeywords (keywords for image search if NeedsImage is true)
            """
    
    async def analyze_content(self, context: Dict[str, str]) -> str:
        """
        Analyze PDF content and segment it into logical slides.
        
        Args:
            context: Dictionary containing the PDF content
            
        Returns:
            JSON string with the segmented slide data
            
        Raises:
            ValueError: If PDF content is missing from context
            RuntimeError: If analysis fails
        """
        if "pdf_content" not in context:
            raise ValueError("PDF content is missing from context")
        
        pdf_content = context["pdf_content"]
        
        # Prepare the prompt by replacing placeholders
        prompt = self.prompt_template.replace("{{pdf_content}}", pdf_content)
        
        try:
            # Initialize Gemini model
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate content analysis
            response = model.generate_content(prompt)
            
            # Extract and validate the JSON response
            result = response.text
            
            # Ensure the result is valid JSON
            try:
                # Try to parse as JSON to validate
                json_result = json.loads(result)
                
                # Validate the structure
                self._validate_slide_data(json_result)
                
                # Return the validated JSON as a string
                return json.dumps(json_result)
            except json.JSONDecodeError:
                # If the response is not valid JSON, try to extract JSON from the text
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    json_result = json.loads(json_str)
                    self._validate_slide_data(json_result)
                    return json.dumps(json_result)
                else:
                    raise RuntimeError("Failed to extract valid JSON from the analysis result")
                
        except Exception as e:
            raise RuntimeError(f"Content analysis failed: {str(e)}")
    
    def _validate_slide_data(self, slide_data: List[Dict[str, Any]]) -> None:
        """
        Validate the structure of the slide data.
        
        Args:
            slide_data: List of slide data dictionaries
            
        Raises:
            ValueError: If the slide data is invalid
        """
        if not isinstance(slide_data, list):
            raise ValueError("Slide data must be a list")
        
        for i, slide in enumerate(slide_data):
            if not isinstance(slide, dict):
                raise ValueError(f"Slide {i} must be a dictionary")
            
            # Check required fields
            required_fields = ["SlideNumber", "Title", "Content"]
            for field in required_fields:
                if field not in slide:
                    raise ValueError(f"Slide {i} is missing required field: {field}")
            
            # Validate field types
            if not isinstance(slide["SlideNumber"], int):
                raise ValueError(f"SlideNumber in slide {i} must be an integer")
            
            if not isinstance(slide["Title"], str):
                raise ValueError(f"Title in slide {i} must be a string")
            
            if not isinstance(slide["Content"], list):
                raise ValueError(f"Content in slide {i} must be a list")
            
            # Set default values for optional fields if missing
            if "HasData" not in slide:
                slide["HasData"] = False
            
            if "Data" not in slide:
                slide["Data"] = ""
            
            if "NeedsImage" not in slide:
                slide["NeedsImage"] = False
            
            if "ImageKeywords" not in slide:
                slide["ImageKeywords"] = ""
