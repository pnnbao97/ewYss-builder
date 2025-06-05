#!/usr/bin/env python3
"""
PDFToSlidesConverter - Main Entry Point

This script is the main entry point for the PDF to Academic Slides Converter.
It handles command-line arguments and initializes the orchestrator.
"""

import os
import sys
import json
import asyncio
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from orchestration.pdf_to_slides_orchestrator import PDFToSlidesOrchestrator
from orchestration.semantic_kernel_integration import SemanticKernelFactory, AgentFactory

load_dotenv()  # Load environment variables from .env file if it exists

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
async def main():
    """Main entry point for the PDF to Academic Slides Converter."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Convert PDF to Academic Slides")
    parser.add_argument("pdf_path", help="Path to the PDF file to convert")
    parser.add_argument("--output-dir", "-o", default="output", help="Directory where to save the slides")
    parser.add_argument("--api-key", "-k", help="Gemini API key")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--theme", "-t", default="academic", help="Theme to use (academic, medical, business, technology, creative)")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_configuration(args.config)
    
    # Get API key (priority: command line > config file > environment variable)
    api_key = GEMINI_API_KEY or args.api_key or config.get("api_key")
    
    if not api_key:
        print("Error: Gemini API key not provided.")
        print("Please provide an API key using one of the following methods:")
        print("  - Command-line argument: --api-key YOUR_API_KEY")
        print("  - Configuration file: api_key field in config.json")
        print("  - Environment variable: GEMINI_API_KEY")
        return 1
    
    # Validate PDF path
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"PDF Path: {args.pdf_path}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Theme: {args.theme}")
    
    try:
        # Initialize Semantic Kernel
        print("Initializing Semantic Kernel...")
        kernel = SemanticKernelFactory.create_kernel(api_key)
        agent_factory = AgentFactory(kernel)
        
        # Initialize orchestrator with Semantic Kernel
        print("Initializing orchestrator...")
        orchestrator = PDFToSlidesOrchestrator(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            api_key=api_key,
            theme_name=args.theme,
            agent_factory=agent_factory
        )
        
        # Run conversion
        print("Starting conversion process...")
        result = await orchestrator.convert_pdf_to_slides_async()
        
        print("Conversion completed successfully!")
        print(result)
        
        # Open the result in browser if available
        presentation_path = os.path.join(args.output_dir, "presentation", "index.html")
        if os.path.exists(presentation_path):
            print(f"Presentation available at: {presentation_path}")
            
            # Try to open in browser on supported platforms
            try:
                import webbrowser
                webbrowser.open(f"file://{os.path.abspath(presentation_path)}")
            except Exception as e:
                print(f"Note: Could not automatically open presentation in browser: {str(e)}")
        
        return 0
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def load_configuration(config_path: Optional[str]) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary with configuration values
    """
    if not config_path:
        # Check for default config locations
        default_locations = [
            "config.json",
            os.path.join("config", "config.json"),
            os.path.expanduser("~/.pdf2slides/config.json")
        ]
        
        for location in default_locations:
            if os.path.exists(location):
                config_path = location
                break
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load configuration from {config_path}: {str(e)}")
    
    return {}


if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
