"""
PDFToSlidesConverter Orchestrator Module

This module contains the main orchestrator class that coordinates the entire process
of converting PDF documents to academic slides using multiple specialized agents.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional

from .context_manager import ContextManager
from .semantic_kernel_integration import AgentFactory
from ..skills.native_skills.pdf_extraction import PDFExtractionSkill
from ..skills.native_skills.file_system import FileSystemSkill
from ..skills.native_skills.image_processing import ImageProcessingSkill


class PDFToSlidesOrchestrator:
    """
    Main orchestrator for the PDF to Slides conversion process.
    Coordinates multiple specialized agents to convert PDF documents into academic slides.
    """
    
    def __init__(self, pdf_path: str, output_dir: str, api_key: str, theme_name: str = "academic", agent_factory: Optional[AgentFactory] = None):
        """
        Initialize the orchestrator with the PDF path, output directory, and API key.
        
        Args:
            pdf_path: Path to the PDF file to convert
            output_dir: Directory where the slides will be saved
            api_key: Gemini API key for LLM access
            theme_name: Name of the theme to use (default: academic)
            agent_factory: Optional AgentFactory instance for creating agents
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.api_key = api_key
        self.theme_name = theme_name
        self.context_manager = ContextManager()
        self.agent_factory = agent_factory
        
        # Initialize native skills
        self.pdf_tool = PDFExtractionSkill()
        self.file_tool = FileSystemSkill()
        self.image_tool = ImageProcessingSkill()
        
        # Load theme
        self.theme = self._load_theme(theme_name)
    
    def _load_theme(self, theme_name: str) -> Dict[str, Any]:
        """
        Load a theme from the themes directory.
        
        Args:
            theme_name: Name of the theme to load
            
        Returns:
            Theme configuration as a dictionary
        """
        # Get the base directory of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Construct the path to the theme file
        theme_path = os.path.join(base_dir, "themes", theme_name, "theme.json")
        
        # Load the theme
        if os.path.exists(theme_path):
            with open(theme_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print(f"Warning: Theme '{theme_name}' not found. Using default theme.")
            return {
                "name": "Default",
                "colors": {
                    "primary": "#2c3e50",
                    "secondary": "#3498db",
                    "accent": "#e74c3c",
                    "background": "#f5f9fa",
                    "text": "#333333"
                },
                "fonts": {
                    "heading": "'Roboto', sans-serif",
                    "body": "'Open Sans', sans-serif"
                }
            }
    
    async def convert_pdf_to_slides_async(self) -> str:
        """
        Convert a PDF document to academic slides asynchronously.
        
        Returns:
            A string with the result of the conversion process
        """
        try:
            # Step 1: Extract PDF content
            print("Extracting PDF content...")
            pdf_content = await self.pdf_tool.extract_content(self.pdf_path)
            self.context_manager.store_result("pdf_content", pdf_content)
            
            # Step 2: Analyze content using Content Analyzer Agent
            print("Analyzing content...")
            content_analyzer_agent = self.agent_factory.create_content_analyzer_agent()
            content_analysis_response = await content_analyzer_agent.invoke_async(f"""
            Please analyze the following PDF content and segment it into logical slides:
            
            {pdf_content}
            
            Return a structured JSON array of slide data, where each slide includes:
            - SlideNumber
            - Title
            - Content (array of points)
            - HasData (boolean indicating if the slide contains data that needs visualization)
            - Data (string representation of data if HasData is true)
            - NeedsImage (boolean indicating if the slide needs an illustrative image)
            - ImageKeywords (keywords for image search if NeedsImage is true)
            """)
            
            # Extract and validate the JSON response
            content_analysis = self._extract_json_from_response(content_analysis_response.content)
            self.context_manager.store_result("content_analysis", content_analysis)
            
            # Step 3: Process slides in parallel
            print("Processing slides...")
            slide_results = await self.process_slides_in_parallel(json.loads(content_analysis))
            self.context_manager.store_result("slides", json.dumps(slide_results))
            
            # Step 4: Generate final presentation using Orchestrator Agent
            print("Generating final presentation...")
            orchestrator_agent = self.agent_factory.create_orchestrator_agent()
            presentation_response = await orchestrator_agent.invoke_async(f"""
            Please generate a complete academic presentation from the provided slides.
            
            PDF Path: {self.pdf_path}
            Output Directory: {self.output_dir}
            Theme: {json.dumps(self.theme)}
            Slides: {json.dumps(slide_results)}
            
            Generate the final presentation HTML that combines all slides into a cohesive presentation.
            Include navigation controls, transitions, and a consistent theme across all slides.
            """)
            
            # Process the presentation response
            await self._generate_presentation_files(slide_results)
            
            return f"Presentation generated successfully at {os.path.join(self.output_dir, 'presentation')}"
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def process_slides_in_parallel(self, slide_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process all slides in parallel using asyncio.
        
        Args:
            slide_data_list: List of slide data dictionaries
            
        Returns:
            List of processed slide results
        """
        # Process each slide in parallel
        tasks = []
        for slide_data in slide_data_list:
            tasks.append(self.process_single_slide(slide_data))
        
        # Wait for all slides to be processed
        slide_results = await asyncio.gather(*tasks)
        
        return slide_results
    
    async def process_single_slide(self, slide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single slide using multiple specialized agents.
        
        Args:
            slide_data: Dictionary with the slide data
            
        Returns:
            Dictionary with the processed slide result
        """
        slide_data_json = json.dumps(slide_data)
        
        # Step 3.1: Get theme and layout using Theme Layout Agent
        theme_layout_agent = self.agent_factory.create_theme_layout_agent()
        theme_response = await theme_layout_agent.invoke_async(f"""
        I need to select an appropriate theme and layout for the following slide:
        
        Slide Data: {slide_data_json}
        Base Theme: {json.dumps(self.theme)}
        
        Please provide a theme and layout configuration that best suits this slide content,
        building upon the base theme provided.
        """)
        
        theme_result = self._extract_json_from_response(theme_response.content)
        
        # Step 3.2: Process data visualization if needed using Data Visualization Agent
        visualization = ""
        if slide_data.get("HasData", False):
            data_viz_agent = self.agent_factory.create_data_visualization_agent()
            viz_response = await data_viz_agent.invoke_async(f"""
            I need to create a visualization for the following data:
            
            Data: {slide_data.get("Data", "")}
            Slide Context: {slide_data_json}
            
            Please generate JavaScript code using Chart.js to visualize this data appropriately.
            """)
            
            visualization = viz_response.content
        
        # Step 3.3: Search for images if needed using Image Search Agent
        image_url = ""
        if slide_data.get("NeedsImage", False):
            image_search_agent = self.agent_factory.create_image_search_agent()
            img_response = await image_search_agent.invoke_async(f"""
            I need to find an appropriate image for the following slide content:
            
            Slide Data: {slide_data_json}
            Image Keywords: {slide_data.get("ImageKeywords", "")}
            
            Please search for and return the URL of an image that best illustrates this slide content.
            """)
            
            image_url = img_response.content.strip()
        
        # Step 3.4: Generate slide HTML using Slide Generator Agent
        slide_gen_agent = self.agent_factory.create_slide_generator_agent()
        slide_response = await slide_gen_agent.invoke_async(f"""
        I need to generate HTML code for a slide with the following components:
        
        Slide Data: {slide_data_json}
        Theme and Layout: {theme_result}
        Visualization (if any): {visualization}
        Image URL (if any): {image_url}
        
        Please generate complete HTML code for this slide, including all necessary CSS and JavaScript.
        The HTML should be high-quality academic slide with smooth animations and professional design.
        Include appropriate icons for headings (like key icon for "Key Points" sections).
        Make sure the slide is responsive and visually appealing.
        """)
        
        slide_html = slide_response.content
        
        # Step 3.5: Generate narration using Narration Agent
        narration_agent = self.agent_factory.create_narration_agent()
        narration_response = await narration_agent.invoke_async(f"""
        I need to create a detailed narration script for the following slide:
        
        Slide HTML: {slide_html}
        Slide Data: {slide_data_json}
        
        Please generate a comprehensive narration script (300-500 words) that explains this slide content in detail, including:
        - Introduction to the slide topic
        - Explanation of all key points
        - Context and background information
        - Connections to broader concepts
        - Conclusion or transition to the next slide
        
        The narration should be academic in tone but engaging, suitable for a lecture or presentation.
        """)
        
        narration = narration_response.content
        
        # Return combined result
        return {
            "SlideNumber": slide_data.get("SlideNumber", 0),
            "Title": slide_data.get("Title", ""),
            "SlideHtml": slide_html,
            "Narration": narration
        }
    
    async def _generate_presentation_files(self, slide_results: List[Dict[str, Any]]) -> None:
        """
        Generate the final presentation files.
        
        Args:
            slide_results: List of processed slide results
        """
        # Create presentation directory
        presentation_dir = os.path.join(self.output_dir, "presentation")
        os.makedirs(presentation_dir, exist_ok=True)
        
        # Extract PDF filename for the title
        pdf_filename = os.path.basename(self.pdf_path)
        title = os.path.splitext(pdf_filename)[0]
        
        # Generate index.html
        index_html = self._generate_index_html(title, slide_results)
        await self.file_tool.save_to_file(index_html, os.path.join(presentation_dir, "index.html"))
        
        # Generate individual slide files
        for i, slide in enumerate(slide_results):
            slide_html = slide.get("SlideHtml", "")
            slide_path = os.path.join(presentation_dir, f"slide_{i+1}.html")
            await self.file_tool.save_to_file(slide_html, slide_path)
            
            # Save narration if available
            narration = slide.get("Narration", "")
            if narration:
                narration_path = os.path.join(presentation_dir, f"narration_{i+1}.txt")
                await self.file_tool.save_to_file(narration, narration_path)
        
        # Generate CSS and JS files
        await self._generate_assets(presentation_dir)
    
    def _generate_index_html(self, title: str, slides_data: List[Dict[str, Any]]) -> str:
        """
        Generate the index.html file that combines all slides.
        
        Args:
            title: Title of the presentation
            slides_data: List of slide data
            
        Returns:
            HTML content for index.html
        """
        # Create HTML header
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Academic Presentation</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/remixicon@2.5.0/fonts/remixicon.css" rel="stylesheet">
</head>
<body>
    <div class="presentation-container">
        <div class="controls">
            <button id="prev-slide" title="Previous Slide"><i class="ri-arrow-left-line"></i></button>
            <span id="slide-counter">1 / {len(slides_data)}</span>
            <button id="next-slide" title="Next Slide"><i class="ri-arrow-right-line"></i></button>
            <button id="toggle-narration" title="Toggle Narration"><i class="ri-volume-up-line"></i></button>
        </div>
        <div class="slides-container">
"""
        
        # Add each slide
        for i, slide in enumerate(slides_data):
            slide_html = slide.get("SlideHtml", "")
            slide_number = i + 1
            
            # Clean up slide HTML if needed
            if "<html" in slide_html:
                # Extract just the body content if it's a complete HTML document
                import re
                body_match = re.search(r'<body[^>]*>(.*?)</body>', slide_html, re.DOTALL)
                if body_match:
                    slide_html = body_match.group(1).strip()
            
            # Add slide div
            html += f"""
            <div class="slide" id="slide-{slide_number}" data-slide-number="{slide_number}" style="display: {'' if i == 0 else 'none'}">
                {slide_html}
            </div>
"""
        
        # Add narration panel
        html += """
        </div>
        <div class="narration-panel" style="display: none;">
            <div class="narration-header">
                <h3>Narration</h3>
                <button id="close-narration"><i class="ri-close-line"></i></button>
            </div>
            <div class="narration-content" id="narration-content"></div>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>
"""
        
        return html
    
    async def _generate_assets(self, presentation_dir: str) -> None:
        """
        Generate CSS and JS files for the presentation.
        
        Args:
            presentation_dir: Directory where to save the assets
        """
        # Generate CSS based on theme
        css = self._generate_css()
        await self.file_tool.save_to_file(css, os.path.join(presentation_dir, "styles.css"))
        
        # Generate JS
        js = self._generate_js()
        await self.file_tool.save_to_file(js, os.path.join(presentation_dir, "script.js"))
    
    def _generate_css(self) -> str:
        """
        Generate CSS for the presentation based on the theme.
        
        Returns:
            CSS content
        """
        primary_color = self.theme.get("colors", {}).get("primary", "#2c3e50")
        secondary_color = self.theme.get("colors", {}).get("secondary", "#3498db")
        accent_color = self.theme.get("colors", {}).get("accent", "#e74c3c")
        background_color = self.theme.get("colors", {}).get("background", "#f5f9fa")
        text_color = self.theme.get("colors", {}).get("text", "#333333")
        
        heading_font = self.theme.get("fonts", {}).get("heading", "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        body_font = self.theme.get("fonts", {}).get("body", "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        
        css = f"""
body {{
    font-family: {body_font};
    margin: 0;
    padding: 0;
    background-color: {background_color};
    overflow: hidden;
    color: {text_color};
}}

.presentation-container {{
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    position: relative;
}}

.controls {{
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px;
    background-color: {primary_color};
    color: white;
}}

.controls button {{
    background: none;
    border: none;
    color: white;
    font-size: 1.2rem;
    cursor: pointer;
    margin: 0 10px;
    padding: 5px 10px;
    border-radius: 4px;
    transition: background-color 0.3s;
}}

.controls button:hover {{
    background-color: {secondary_color};
}}

#slide-counter {{
    margin: 0 15px;
    font-size: 0.9rem;
}}

.slides-container {{
    flex: 1;
    overflow: hidden;
    position: relative;
    background-color: white;
}}

.slide {{
    width: 100%;
    height: 100%;
    padding: 20px;
    box-sizing: border-box;
    overflow: auto;
}}

.narration-panel {{
    position: absolute;
    right: 0;
    top: 0;
    width: 300px;
    height: 100%;
    background-color: white;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    z-index: 100;
    display: flex;
    flex-direction: column;
}}

.narration-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    background-color: #f0f0f0;
    border-bottom: 1px solid #ddd;
}}

.narration-header h3 {{
    margin: 0;
    font-size: 1rem;
}}

.narration-header button {{
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
}}

.narration-content {{
    flex: 1;
    padding: 15px;
    overflow-y: auto;
    font-size: 0.9rem;
    line-height: 1.5;
}}

/* Slide themes */
.slide-academic {{
    background-color: #f0f8ff;
    color: {text_color};
}}

.slide-medical {{
    background-color: #f0fff0;
    color: {text_color};
}}

.slide-data {{
    background-color: #fff8f0;
    color: {text_color};
}}

/* Common slide elements */
.slide h1 {{
    color: {primary_color};
    border-bottom: 2px solid {secondary_color};
    padding-bottom: 10px;
    margin-top: 0;
    font-family: {heading_font};
}}

.slide h2 {{
    color: {secondary_color};
    font-family: {heading_font};
}}

.slide ul, .slide ol {{
    margin-left: 20px;
}}

.slide li {{
    margin-bottom: 10px;
}}

.slide img {{
    max-width: 100%;
    max-height: 60vh;
    display: block;
    margin: 0 auto;
}}

.slide .chart-container {{
    width: 100%;
    height: 300px;
    margin: 20px 0;
}}

/* Animations */
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
}}

.fade-in {{
    animation: fadeIn 0.5s ease-in-out;
}}

/* Responsive design */
@media (max-width: 768px) {{
    .narration-panel {{
        width: 100%;
    }}
}}
"""
        
        return css
    
    def _generate_js(self) -> str:
        """
        Generate JavaScript for the presentation.
        
        Returns:
            JavaScript content
        """
        js = """
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const slides = document.querySelectorAll('.slide');
    const prevButton = document.getElementById('prev-slide');
    const nextButton = document.getElementById('next-slide');
    const slideCounter = document.getElementById('slide-counter');
    const toggleNarrationButton = document.getElementById('toggle-narration');
    const narrationPanel = document.querySelector('.narration-panel');
    const closeNarrationButton = document.getElementById('close-narration');
    const narrationContent = document.getElementById('narration-content');
    
    // State
    let currentSlideIndex = 0;
    let narrationVisible = false;
    
    // Functions
    function showSlide(index) {
        // Hide all slides
        slides.forEach(slide => {
            slide.style.display = 'none';
        });
        
        // Show current slide
        slides[index].style.display = 'block';
        slides[index].classList.add('fade-in');
        
        // Update counter
        slideCounter.textContent = `${index + 1} / ${slides.length}`;
        
        // Update narration if visible
        if (narrationVisible) {
            updateNarration(index);
        }
        
        // Initialize any charts in the current slide
        initializeCharts(slides[index]);
    }
    
    function nextSlide() {
        if (currentSlideIndex < slides.length - 1) {
            currentSlideIndex++;
            showSlide(currentSlideIndex);
        }
    }
    
    function prevSlide() {
        if (currentSlideIndex > 0) {
            currentSlideIndex--;
            showSlide(currentSlideIndex);
        }
    }
    
    function toggleNarration() {
        narrationVisible = !narrationVisible;
        narrationPanel.style.display = narrationVisible ? 'flex' : 'none';
        
        if (narrationVisible) {
            updateNarration(currentSlideIndex);
        }
    }
    
    async function updateNarration(index) {
        const slideNumber = index + 1;
        try {
            const response = await fetch(`narration_${slideNumber}.txt`);
            if (response.ok) {
                const text = await response.text();
                narrationContent.textContent = text;
            } else {
                narrationContent.textContent = 'No narration available for this slide.';
            }
        } catch (error) {
            narrationContent.textContent = 'No narration available for this slide.';
        }
    }
    
    function initializeCharts(slide) {
        const chartContainers = slide.querySelectorAll('.chart-container');
        chartContainers.forEach(container => {
            if (container.dataset.initialized) return;
            
            const canvas = container.querySelector('canvas');
            if (!canvas) return;
            
            const chartType = container.dataset.chartType || 'bar';
            const chartData = JSON.parse(container.dataset.chartData || '{}');
            
            new Chart(canvas, {
                type: chartType,
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
            
            container.dataset.initialized = 'true';
        });
    }
    
    // Event listeners
    prevButton.addEventListener('click', prevSlide);
    nextButton.addEventListener('click', nextSlide);
    toggleNarrationButton.addEventListener('click', toggleNarration);
    closeNarrationButton.addEventListener('click', toggleNarration);
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowRight' || e.key === ' ') {
            nextSlide();
        } else if (e.key === 'ArrowLeft') {
            prevSlide();
        } else if (e.key === 'n') {
            toggleNarration();
        }
    });
    
    // Initialize first slide
    showSlide(currentSlideIndex);
});
"""
        
        return js
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from a response text.
        
        Args:
            response_text: Response text that may contain JSON
            
        Returns:
            Extracted JSON string
        """
        # Try to parse as JSON directly
        try:
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from the text
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                # Validate JSON
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON found, return the original text
        return response_text
