"""
PDF Extraction Skill for PDFToSlidesConverter using PyMuPDF with asyncio concurrency

This module provides functions to extract content from PDF files using PyMuPDF (fitz),
including text, tables, images, and layout information. It uses asyncio semaphore
for concurrent processing to improve performance.
"""

import os
import json
import asyncio
import tempfile
from typing import Dict, List, Any, Tuple, Optional

import fitz  # PyMuPDF


class PDFExtractionSkill:
    """
    Skill for extracting content from PDF files using PyMuPDF with asyncio concurrency.
    """
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """
        Initialize the PDF extraction skill.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks (default: 5)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.loop = asyncio.get_event_loop()
    
    async def extract_content(self, pdf_path: str, start_page: int = None, end_page: int = None) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            start_page: First page to extract (1-based index, optional)
            end_page: Last page to extract (1-based index, optional)
            
        Returns:
            Extracted text content
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Adjust page range
            start_page = max(0, (start_page or 1) - 1)  # Convert to 0-based index
            end_page = min(doc.page_count - 1, (end_page or doc.page_count) - 1)
            
            # Extract basic metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "page_count": doc.page_count
            }
            
            # Extract content from each page concurrently
            content = []
            content.append(f"Title: {metadata['title']}")
            content.append(f"Author: {metadata['author']}")
            content.append(f"Pages: {doc.page_count}")
            content.append("\n")
            
            # Process pages concurrently with semaphore
            tasks = []
            for page_num in range(start_page, end_page + 1):
                tasks.append(self._extract_page_content(doc, page_num))
            
            # Wait for all tasks to complete
            page_contents = await asyncio.gather(*tasks)
            
            # Add page contents in order
            for page_num, page_content in enumerate(page_contents, start=start_page + 1):
                content.append(f"--- Page {page_num} ---")
                content.append(page_content)
            
            return "\n".join(content)
            
        except Exception as e:
            raise Exception(f"Error extracting content from PDF: {str(e)}")
    
    async def extract_structured_content(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract structured content from a PDF file, including text, tables, and images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with structured content
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "page_count": doc.page_count
            }
            
            # Process pages concurrently with semaphore
            tasks = []
            for page_num in range(doc.page_count):
                tasks.append(self._extract_structured_page_content(doc, page_num))
            
            # Wait for all tasks to complete
            pages = await asyncio.gather(*tasks)
            
            return {
                "metadata": metadata,
                "pages": pages
            }
            
        except Exception as e:
            raise Exception(f"Error extracting structured content from PDF: {str(e)}")
    
    async def extract_images(self, pdf_path: str, output_dir: str) -> List[str]:
        """
        Extract images from a PDF file and save them to the output directory.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory where to save the extracted images
            
        Returns:
            List of paths to the extracted images
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Process pages concurrently with semaphore
            tasks = []
            for page_num in range(doc.page_count):
                tasks.append(self._extract_page_images(doc, page_num, output_dir))
            
            # Wait for all tasks to complete and flatten the results
            image_paths_nested = await asyncio.gather(*tasks)
            image_paths = [path for paths in image_paths_nested for path in paths]
            
            return image_paths
            
        except Exception as e:
            raise Exception(f"Error extracting images from PDF: {str(e)}")
    
    async def _extract_page_content(self, doc: fitz.Document, page_num: int) -> str:
        """
        Extract content from a single page with semaphore control.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            
        Returns:
            Extracted page content as string
        """
        async with self.semaphore:
            # Use run_in_executor to prevent blocking the event loop
            return await self.loop.run_in_executor(None, self._extract_page_content_sync, doc, page_num)
    
    def _extract_page_content_sync(self, doc: fitz.Document, page_num: int) -> str:
        """
        Synchronous function to extract content from a single page.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            
        Returns:
            Extracted page content as string
        """
        page = doc[page_num]
        content = []
        
        # Extract text with layout preservation
        text = page.get_text("text")
        content.append(text)
        
        # Extract tables if present
        tables = self._extract_tables(page)
        if tables:
            content.append("\nTables on this page:")
            for i, table in enumerate(tables):
                content.append(f"\nTable {i+1}:")
                content.append(self._format_table(table))
        
        return "\n".join(content)
    
    async def _extract_structured_page_content(self, doc: fitz.Document, page_num: int) -> Dict[str, Any]:
        """
        Extract structured content from a single page with semaphore control.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            
        Returns:
            Dictionary with structured page content
        """
        async with self.semaphore:
            # Use run_in_executor to prevent blocking the event loop
            return await self.loop.run_in_executor(None, self._extract_structured_page_content_sync, doc, page_num)
    
    def _extract_structured_page_content_sync(self, doc: fitz.Document, page_num: int) -> Dict[str, Any]:
        """
        Synchronous function to extract structured content from a single page.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            
        Returns:
            Dictionary with structured page content
        """
        page = doc[page_num]
        
        # Extract text blocks
        blocks = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"]
                    block_text += "\n"
                
                if block_text.strip():
                    blocks.append({
                        "text": block_text.strip(),
                        "bbox": block["bbox"],
                        "type": "text"
                    })
        
        # Extract tables
        tables = self._extract_tables(page)
        table_blocks = []
        for table in tables:
            table_blocks.append({
                "content": table,
                "type": "table"
            })
        
        # Extract images
        images = self._extract_images(page)
        image_blocks = []
        for img in images:
            image_blocks.append({
                "bbox": img["bbox"],
                "type": "image",
                "image_data": img["image_data"] if "image_data" in img else None
            })
        
        # Return page data
        return {
            "page_number": page_num + 1,
            "text_blocks": blocks,
            "tables": table_blocks,
            "images": image_blocks
        }
    
    async def _extract_page_images(self, doc: fitz.Document, page_num: int, output_dir: str) -> List[str]:
        """
        Extract images from a single page with semaphore control.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            output_dir: Directory where to save the extracted images
            
        Returns:
            List of paths to the extracted images
        """
        async with self.semaphore:
            # Use run_in_executor to prevent blocking the event loop
            return await self.loop.run_in_executor(None, self._extract_page_images_sync, doc, page_num, output_dir)
    
    def _extract_page_images_sync(self, doc: fitz.Document, page_num: int, output_dir: str) -> List[str]:
        """
        Synchronous function to extract images from a single page.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based index)
            output_dir: Directory where to save the extracted images
            
        Returns:
            List of paths to the extracted images
        """
        page = doc[page_num]
        image_paths = []
        
        # Get images
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Determine image extension
            image_ext = base_image["ext"]
            
            # Save the image
            image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            image_paths.append(image_path)
        
        return image_paths
    
    def _extract_tables(self, page: fitz.Page) -> List[List[List[str]]]:
        """
        Extract tables from a page using PyMuPDF.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of tables, where each table is a list of rows, and each row is a list of cells
        """
        tables = []
        
        # Try to find tables using built-in table finder
        table_finder = page.find_tables()
        
        if table_finder and table_finder.tables:
            for table in table_finder.tables:
                # Extract table data
                table_data = []
                for row in table.extract():
                    table_data.append([cell or "" for cell in row])
                tables.append(table_data)
        
        return tables
    
    def _extract_images(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """
        Extract images from a page.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of dictionaries with image data
        """
        images = []
        
        # Get images
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            # Get image rectangle
            for img_rect in page.get_image_rects(xref):
                images.append({
                    "bbox": list(img_rect),
                    "xref": xref
                })
        
        return images
    
    def _format_table(self, table: List[List[str]]) -> str:
        """
        Format a table as a string.
        
        Args:
            table: Table data as a list of rows, where each row is a list of cells
            
        Returns:
            Formatted table as a string
        """
        if not table:
            return ""
        
        # Calculate column widths
        col_widths = [0] * len(table[0])
        for row in table:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Format table
        result = []
        
        # Add separator
        separator = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
        result.append(separator)
        
        # Add rows
        for row in table:
            row_str = "|"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    row_str += f" {str(cell):{col_widths[i]}} |"
            result.append(row_str)
            result.append(separator)
        
        return "\n".join(result)


# # Example usage
# async def main():
#     """Example usage of PDFExtractionSkill with asyncio concurrency."""
#     import sys
    
#     if len(sys.argv) < 2:
#         print("Usage: python pdf_extraction.py <pdf_path> [output_dir]")
#         return
    
#     pdf_path = sys.argv[1]
#     output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
#     # Create output directory if it doesn't exist
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Initialize PDF extraction skill with concurrency
#     pdf_tool = PDFExtractionSkill(max_concurrent_tasks=10)
    
#     try:
#         # Extract content
#         print(f"Extracting content from {pdf_path}...")
#         content = await pdf_tool.extract_content(pdf_path)
#         with open(os.path.join(output_dir, "content.txt"), "w", encoding="utf-8") as f:
#             f.write(content)
#         print(f"Content saved to {os.path.join(output_dir, 'content.txt')}")
        
#         # Extract structured content
#         print("Extracting structured content...")
#         structured_content = await pdf_tool.extract_structured_content(pdf_path)
#         with open(os.path.join(output_dir, "structured_content.json"), "w", encoding="utf-8") as f:
#             json.dump(structured_content, f, indent=2)
#         print(f"Structured content saved to {os.path.join(output_dir, 'structured_content.json')}")
        
#         # Extract images
#         print("Extracting images...")
#         images_dir = os.path.join(output_dir, "images")
#         os.makedirs(images_dir, exist_ok=True)
#         image_paths = await pdf_tool.extract_images(pdf_path, images_dir)
#         print(f"Extracted {len(image_paths)} images to {images_dir}")
        
#         print("Done!")
        
#     except Exception as e:
#         print(f"Error: {str(e)}")


# if __name__ == "__main__":
#     asyncio.run(main())
