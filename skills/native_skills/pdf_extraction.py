"""
PDF Extraction Skill for PDFToSlidesConverter

This module provides functionality to extract content from PDF files,
including text, images, and tables.
"""

import os
import json
import asyncio
import tempfile
import subprocess
from typing import Dict, List, Any


class PDFExtractionSkill:
    """
    Provides methods to extract content from PDF files.
    Uses poppler-utils and other tools to extract text, images, and tables.
    """
    
    async def extract_content(self, pdf_path: str) -> str:
        """
        Extract content from a PDF file including text, images, and tables.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            JSON string containing the extracted content
            
        Raises:
            FileNotFoundError: If the PDF file does not exist
            RuntimeError: If extraction fails
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        result = {
            "text": await self.extract_text(pdf_path),
            "images": await self.extract_images(pdf_path),
            "tables": await self.extract_tables(pdf_path)
        }
        
        return json.dumps(result)
    
    async def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file using pdftotext (poppler-utils).
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        # Use poppler-utils to extract text
        process = await asyncio.create_subprocess_exec(
            "pdftotext", "-layout", pdf_path, "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to extract text: {stderr.decode()}")
        
        return stdout.decode()
    
    async def extract_images(self, pdf_path: str) -> List[str]:
        """
        Extract images from a PDF file using pdfimages (poppler-utils).
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of paths to extracted images
        """
        # Create output directory
        output_dir = tempfile.mkdtemp()
        
        # Use pdfimages to extract images
        process = await asyncio.create_subprocess_exec(
            "pdfimages", "-j", pdf_path, os.path.join(output_dir, "img"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to extract images: {stderr.decode()}")
        
        # Get list of extracted images
        image_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
        return image_files
    
    async def extract_tables(self, pdf_path: str) -> List[str]:
        """
        Extract tables from a PDF file.
        Uses tabula-py if available, otherwise returns empty list.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of JSON strings representing tables
        """
        try:
            # Try to import tabula-py
            import tabula
            
            # Extract tables to JSON
            tables = tabula.read_pdf(pdf_path, pages='all', output_format='json')
            
            # Convert to list of JSON strings
            return [json.dumps(table) for table in tables]
            
        except ImportError:
            # If tabula-py is not available, try using tabula-java if installed
            try:
                output_dir = tempfile.mkdtemp()
                output_file = os.path.join(output_dir, "tables.json")
                
                process = await asyncio.create_subprocess_exec(
                    "java", "-jar", "tabula-java.jar", "-p", "all", "-f", "JSON", 
                    "-o", output_file, pdf_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                _, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return []
                
                # Read extracted tables
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        table_json = f.read()
                    return [table_json]
                
                return []
                
            except Exception:
                # If all extraction methods fail, return empty list
                return []
