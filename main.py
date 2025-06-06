#!/usr/bin/env python3
"""
PDF to Academic Slides Converter - Main Entry Point

This script is the main entry point for the PDF to Academic Slides Converter.
It parses command-line arguments and initializes the conversion process.
"""

import os
import sys
import argparse
import asyncio
from typing import Optional
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if it exists

from semantic_kernel import Kernel

from orchestration.semantic_kernel_integration import SemanticKernelFactory, AgentFactory
from orchestration.pdf_to_slides_orchestrator import PDFToSlidesOrchestrator

GEMNINI_API_KEY= os.environ.get("GEMINI_API_KEY")
async def main_async(pdf_path: str, output_dir: str, api_key: str, theme_name: str) -> None:
    """
    Main asynchronous function to convert PDF to slides.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory where to save the slides
        api_key: Gemini API key
        theme_name: Name of the theme to use
    """
    try:
        # Initialize Semantic Kernel
        print("Initializing Semantic Kernel...")
        kernel = SemanticKernelFactory.create_kernel(api_key)
        
        # Create agent factory
        agent_factory = AgentFactory(kernel)
        
        # Create orchestrator
        print(f"Creating orchestrator for PDF: {pdf_path}")
        orchestrator = PDFToSlidesOrchestrator(
            pdf_path=pdf_path,
            output_dir=output_dir,
            api_key=api_key,
            theme_name=theme_name,
            agent_factory=agent_factory
        )
        
        # Convert PDF to slides
        print("Starting conversion process...")
        result = await orchestrator.convert_pdf_to_slides_async()
        
        print(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main() -> None:
    """
    Main function to parse command-line arguments and start the conversion process.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Convert PDF to Academic Slides")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output-dir", "-o", default="output", help="Directory where to save the slides")
    parser.add_argument("--api-key", "-k", help="Gemini API key")
    parser.add_argument("--theme", "-t", default="academic", help="Theme name (default: academic)")
    
    args = parser.parse_args()
    
    # Validate PDF path
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Get API key from environment if not provided
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Gemini API key not provided. Use --api-key option or set GEMINI_API_KEY environment variable.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run the async main function
    asyncio.run(main_async(args.pdf_path, args.output_dir, api_key, args.theme))


if __name__ == "__main__":
    main()
