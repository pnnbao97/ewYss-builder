"""
Enhanced PDF Extraction Skill using LangChain and PyMuPDF with asyncio concurrency

This module provides functions to extract and intelligently chunk content from PDF files 
using LangChain's advanced document processing capabilities combined with PyMuPDF,
including text, tables, images, and smart semantic chunking for LLM processing.
"""

import os
import json
import asyncio
import tempfile
from typing import Dict, List, Any, Tuple, Optional, Union
import re

import fitz  # PyMuPDF
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    MarkdownTextSplitter,
    TokenTextSplitter,
  
)


class PDFExtractionSkill:
    """
    Enhanced skill for extracting and intelligently chunking content from PDF files 
    using LangChain with PyMuPDF fallback.
    """
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """
        Initialize the enhanced PDF extraction skill.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks (default: 5)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.loop = asyncio.get_event_loop()
        
        # Initialize various text splitters
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        self.token_splitter = TokenTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )
        
        # For semantic chunking (requires embeddings model)
        self.semantic_splitter = None  # Will be initialized when needed
    
    async def extract_and_chunk_content(
        self, 
        pdf_path: str, 
        chunking_strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        preserve_tables: bool = True,
        extract_images: bool = False,
        output_dir: str = None
    ) -> Dict[str, Any]:
        """
        Extract content from PDF and intelligently chunk it for LLM processing.
        
        Args:
            pdf_path: Path to the PDF file
            chunking_strategy: Strategy for chunking ("recursive", "semantic", "markdown", "token", "hybrid")
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            preserve_tables: Whether to preserve table structure
            extract_images: Whether to extract images
            output_dir: Directory for saving images (required if extract_images=True)
            
        Returns:
            Dictionary with chunked content, metadata, and optional images
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if extract_images and not output_dir:
            raise ValueError("output_dir is required when extract_images=True")
        
        try:
            # Step 1: Load document using LangChain
            documents = await self._load_pdf_with_langchain(pdf_path, preserve_tables)
            
            # Step 2: Apply chunking strategy
            chunked_docs = await self._apply_chunking_strategy(
                documents, chunking_strategy, chunk_size, chunk_overlap
            )
            
            # Step 3: Extract additional metadata and structure
            structure_info = await self._extract_document_structure(pdf_path)
            
            # Step 4: Extract images if requested
            image_paths = []
            if extract_images:
                image_paths = await self.extract_images(pdf_path, output_dir)
            
            # Step 5: Create presentation-friendly chunks
            presentation_chunks = await self._create_presentation_chunks(chunked_docs)
            
            return {
                "metadata": structure_info["metadata"],
                "raw_documents": documents,
                "chunked_documents": chunked_docs,
                "presentation_chunks": presentation_chunks,
                "document_structure": structure_info["structure"],
                "images": image_paths,
                "chunking_info": {
                    "strategy": chunking_strategy,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "total_chunks": len(chunked_docs)
                }
            }
            
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    async def _load_pdf_with_langchain(self, pdf_path: str, preserve_tables: bool = True) -> List[Document]:
        """
        Load PDF using LangChain loaders with table preservation.
        """
        documents = []
        
        try:
            # Try UnstructuredPDFLoader first for better table handling
            if preserve_tables:
                try:
                    loader = UnstructuredPDFLoader(
                        pdf_path,
                        mode="elements",  # Preserves document structure
                        strategy="fast"   # Balance between speed and accuracy
                    )
                    docs = await asyncio.get_event_loop().run_in_executor(None, loader.load)
                    documents.extend(docs)
                except Exception as e:
                    print(f"UnstructuredPDFLoader failed, falling back to PyMuPDFLoader: {e}")
                    # Fallback to PyMuPDFLoader
                    loader = PyMuPDFLoader(pdf_path)
                    docs = await asyncio.get_event_loop().run_in_executor(None, loader.load)
                    documents.extend(docs)
            else:
                # Use PyMuPDFLoader for simple text extraction
                loader = PyMuPDFLoader(pdf_path)
                docs = await asyncio.get_event_loop().run_in_executor(None, loader.load)
                documents.extend(docs)
                
        except Exception as e:
            # Final fallback to custom PyMuPDF extraction
            print(f"LangChain loaders failed, using custom PyMuPDF: {e}")
            content = await self._extract_with_pymupdf_fallback(pdf_path)
            documents = [Document(page_content=content, metadata={"source": pdf_path})]
        
        return documents
    
    async def _apply_chunking_strategy(
        self, 
        documents: List[Document], 
        strategy: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Document]:
        """
        Apply the specified chunking strategy to documents.
        """
        # Update splitter parameters
        if strategy == "recursive":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
        elif strategy == "markdown":
            splitter = MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif strategy == "token":
            splitter = TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif strategy == "semantic":
            # Note: Semantic chunking requires an embeddings model
            # This is a placeholder - you'll need to provide embeddings
            print("Warning: Semantic chunking requires embeddings model. Falling back to recursive.")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif strategy == "hybrid":
            # Hybrid approach: First semantic/structural, then recursive
            return await self._apply_hybrid_chunking(documents, chunk_size, chunk_overlap)
        else:
            # Default to recursive
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        # Apply chunking
        chunked_docs = await asyncio.get_event_loop().run_in_executor(
            None, splitter.split_documents, documents
        )
        
        return chunked_docs
    
    async def _apply_hybrid_chunking(
        self, 
        documents: List[Document], 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[Document]:
        """
        Apply hybrid chunking strategy combining structural and semantic approaches.
        """
        chunked_docs = []
        
        for doc in documents:
            # First, try to split by structural elements (headers, paragraphs)
            structural_chunks = await self._split_by_structure(doc.page_content)
            
            # Then apply recursive chunking to large structural chunks
            for chunk_text in structural_chunks:
                if len(chunk_text) > chunk_size:
                    # Further split large chunks
                    temp_doc = Document(page_content=chunk_text, metadata=doc.metadata)
                    sub_chunks = self.recursive_splitter.split_documents([temp_doc])
                    chunked_docs.extend(sub_chunks)
                else:
                    # Keep small chunks as is
                    chunked_docs.append(Document(
                        page_content=chunk_text, 
                        metadata=doc.metadata
                    ))
        
        return chunked_docs
    
    async def _split_by_structure(self, text: str) -> List[str]:
        """
        Split text by structural elements like headers, paragraphs, etc.
        """
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if this looks like a header (short line, possibly numbered/titled)
            is_header = (
                len(paragraph.split('\n')[0]) < 100 and 
                (paragraph.startswith('#') or 
                 any(paragraph.lower().startswith(word) for word in ['chương', 'bài', 'phần', 'mục', 'chapter', 'section']) or
                 paragraph.isupper())
            )
            
            if is_header and current_chunk:
                # Start new chunk with header
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
            else:
                current_chunk += paragraph + '\n\n'
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _extract_document_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract document structure and metadata using PyMuPDF.
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "page_count": doc.page_count,
                "file_path": pdf_path
            }
            
            # Extract table of contents
            toc = doc.get_toc()
            
            # Extract font information for structure analysis
            fonts_info = await self._analyze_document_fonts(doc)
            
            # Identify potential sections and headers
            structure = {
                "table_of_contents": toc,
                "fonts_analysis": fonts_info,
                "estimated_sections": await self._estimate_sections(doc, toc)
            }
            
            doc.close()
            
            return {
                "metadata": metadata,
                "structure": structure
            }
            
        except Exception as e:
            return {
                "metadata": {"file_path": pdf_path, "error": str(e)},
                "structure": {}
            }
    
    async def _analyze_document_fonts(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        Analyze fonts used in the document to identify headers and structure.
        """
        font_info = {}
        
        for page_num in range(min(5, doc.page_count)):  # Analyze first 5 pages
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font = span.get("font", "")
                            size = span.get("size", 0)
                            flags = span.get("flags", 0)
                            
                            key = f"{font}_{size}_{flags}"
                            if key not in font_info:
                                font_info[key] = {
                                    "font": font,
                                    "size": size,
                                    "flags": flags,
                                    "is_bold": bool(flags & 2**4),
                                    "is_italic": bool(flags & 2**1),
                                    "count": 0,
                                    "sample_text": ""
                                }
                            
                            font_info[key]["count"] += 1
                            if len(font_info[key]["sample_text"]) < 100:
                                font_info[key]["sample_text"] += span.get("text", "")
        
        return font_info
    
    async def _estimate_sections(self, doc: fitz.Document, toc: List) -> List[Dict[str, Any]]:
        """
        Estimate document sections based on TOC and text analysis.
        """
        sections = []
        
        if toc:
            # Use table of contents
            for item in toc:
                level, title, page = item
                sections.append({
                    "title": title,
                    "level": level,
                    "page": page,
                    "type": "toc_section"
                })
        else:
            # Try to identify sections by text patterns
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # Look for potential headers
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if self._is_likely_header(line):
                        sections.append({
                            "title": line,
                            "page": page_num + 1,
                            "type": "estimated_header",
                            "confidence": self._calculate_header_confidence(line, lines, i)
                        })
        
        return sections
    
    def _is_likely_header(self, line: str) -> bool:
        """
        Determine if a line is likely to be a header.
        """
        if not line or len(line) > 200:
            return False
        
        # Check for common header patterns
        header_patterns = [
            line.isupper(),
            line.startswith('#'),
            any(line.lower().startswith(word) for word in ['chương', 'bài', 'phần', 'mục', 'chapter', 'section']),
            line.endswith(':') and len(line) < 100,
            bool(re.match(r'^\d+\.?\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]', line))
        ]
        
        return any(header_patterns)
    
    def _calculate_header_confidence(self, line: str, all_lines: List[str], line_index: int) -> float:
        """
        Calculate confidence that a line is a header.
        """
        confidence = 0.0
        
        # Length factor
        if 10 <= len(line) <= 100:
            confidence += 0.3
        
        # Position factor
        if line_index == 0 or (line_index > 0 and not all_lines[line_index - 1].strip()):
            confidence += 0.2
        
        # Formatting factors
        if line.isupper():
            confidence += 0.3
        if line.endswith(':'):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    async def _create_presentation_chunks(self, chunked_docs: List[Document]) -> List[Dict[str, Any]]:
        """
        Create presentation-friendly chunks optimized for slide generation.
        """
        presentation_chunks = []
        
        for i, doc in enumerate(chunked_docs):
            content = doc.page_content.strip()
            
            # Analyze content type
            content_type = self._analyze_content_type(content)
            
            # Extract key points
            key_points = self._extract_key_points(content)
            
            # Suggest slide structure
            slide_structure = self._suggest_slide_structure(content, content_type)
            
            presentation_chunks.append({
                "chunk_id": i,
                "content": content,
                "content_type": content_type,
                "key_points": key_points,
                "slide_structure": slide_structure,
                "metadata": doc.metadata,
                "word_count": len(content.split()),
                "estimated_slides": max(1, len(key_points) // 3)  # Rough estimate
            })
        
        return presentation_chunks
    
    def _analyze_content_type(self, content: str) -> str:
        """
        Analyze the type of content (text, list, table, etc.)
        """
        if '|' in content and content.count('|') > 5:
            return "table"
        elif content.count('\n-') > 2 or content.count('\n•') > 2:
            return "list"
        elif any(word in content.lower() for word in ['hình', 'biểu đồ', 'figure', 'chart']):
            return "figure_reference"
        elif len(content.split('\n')) > 10:
            return "long_text"
        else:
            return "paragraph"
    
    def _extract_key_points(self, content: str) -> List[str]:
        """
        Extract key points from content for slide generation.
        """
        key_points = []
        
        sentences = content.replace('\n', ' ').split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                # Simple heuristic for important sentences
                importance_score = 0
                importance_words = ['quan trọng', 'chính', 'cần', 'phải', 'important', 'key', 'main', 'essential']
                for word in importance_words:
                    if word in sentence.lower():
                        importance_score += 1
                
                if importance_score > 0 or sentence.startswith(('Đầu tiên', 'Thứ hai', 'Cuối cùng', 'First', 'Second', 'Finally')):
                    key_points.append(sentence)
        
        return key_points[:5]  # Limit to top 5 key points
    
    def _suggest_slide_structure(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        Suggest slide structure based on content analysis.
        """
        if content_type == "table":
            return {
                "type": "data_slide",
                "layout": "table",
                "title_suggestion": "Dữ liệu và Thống kê"
            }
        elif content_type == "list":
            return {
                "type": "bullet_slide",
                "layout": "bullet_points",
                "title_suggestion": "Các Điểm Chính"
            }
        elif content_type == "long_text":
            return {
                "type": "content_slide",
                "layout": "text_heavy",
                "title_suggestion": "Nội dung Chi tiết",
                "suggestion": "Nên chia thành nhiều slide"
            }
        else:
            return {
                "type": "standard_slide",
                "layout": "title_content",
                "title_suggestion": "Thông tin"
            }
    
    async def _extract_with_pymupdf_fallback(self, pdf_path: str) -> str:
        """
        Fallback extraction using pure PyMuPDF when LangChain fails.
        """
        doc = fitz.open(pdf_path)
        content = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            content.append(f"--- Trang {page_num + 1} ---")
            content.append(page.get_text())
        
        doc.close()
        return "\n".join(content)
    
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
            doc = fitz.open(pdf_path)
            image_paths = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    image_paths.append(image_path)
            
            doc.close()
            return image_paths
            
        except Exception as e:
            raise Exception(f"Error extracting images from PDF: {str(e)}")