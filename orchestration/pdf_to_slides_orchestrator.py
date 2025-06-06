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
from skills.native_skills.pdf_extraction import PDFExtractionSkill
from skills.native_skills.file_system import FileSystemSkill
from skills.native_skills.image_processing import ImageProcessingSkill


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
            pdf_content = await self.pdf_tool.extract_and_chunk_content(self.pdf_path)
            self.context_manager.store_result("pdf_content", pdf_content)
            print(self.context_manager.get_result("pdf_content"))
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
            
            # Step 2: Analyze content using Content Analyzer Agent
            print("Analyzing content...")
            content_analyzer_agent = self.agent_factory.create_content_analyzer_agent()
            response = await content_analyzer_agent.get_response(pdf_content)
            print(f"Content analysis response: {response.content}")
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
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from a response text.
        
        Args:
            response_text: Response text that may contain JSON
            
        Returns:
            Extracted JSON as a string
        """
        # Try to find JSON in the response
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        
        if json_match:
            # Extract JSON from code block
            json_str = json_match.group(1)
        else:
            # Assume the entire response is JSON
            json_str = response_text
        
        # Clean up the JSON string
        json_str = json_str.strip()
        
        # Validate JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # If JSON is invalid, try to fix common issues
            # Remove any non-JSON text before or after
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
                
                # Try to validate again
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # If still invalid, return as is and let the caller handle it
                    return json_str
            
            return json_str
    
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
        # Extract theme colors
        primary_color = self.theme.get("colors", {}).get("primary", "#2c3e50")
        secondary_color = self.theme.get("colors", {}).get("secondary", "#3498db")
        accent_color = self.theme.get("colors", {}).get("accent", "#e74c3c")
        background_color = self.theme.get("colors", {}).get("background", "#f5f9fa")
        text_color = self.theme.get("colors", {}).get("text", "#333333")
        
        # Extract theme fonts
        heading_font = self.theme.get("fonts", {}).get("heading", "'Roboto', sans-serif")
        body_font = self.theme.get("fonts", {}).get("body", "'Open Sans', sans-serif")
        
        # Generate CSS
        css = f"""
/* Presentation Styles */
:root {{
    --primary-color: {primary_color};
    --secondary-color: {secondary_color};
    --accent-color: {accent_color};
    --background-color: {background_color};
    --text-color: {text_color};
    --heading-font: {heading_font};
    --body-font: {body_font};
}}

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    font-family: var(--body-font);
    background-color: var(--background-color);
    color: var(--text-color);
    line-height: 1.6;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: var(--heading-font);
    color: var(--primary-color);
    margin-bottom: 1rem;
}}

.presentation-container {{
    max-width: 100%;
    min-height: 100vh;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
}}

.controls {{
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 1rem;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 0.5rem 1rem;
    border-radius: 2rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    position: fixed;
    bottom: 2rem;
    z-index: 100;
}}

.controls button {{
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 0 0.5rem;
    cursor: pointer;
    transition: all 0.3s ease;
}}

.controls button:hover {{
    background-color: var(--secondary-color);
    transform: scale(1.1);
}}

#slide-counter {{
    margin: 0 1rem;
    font-weight: bold;
    color: var(--primary-color);
}}

.slides-container {{
    width: 100%;
    max-width: 1200px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    position: relative;
}}

.slide {{
    padding: 2rem;
    min-height: 70vh;
}}

.narration-panel {{
    position: fixed;
    bottom: 0;
    right: 0;
    width: 400px;
    max-height: 50vh;
    background-color: white;
    border-top-left-radius: 8px;
    box-shadow: -2px -2px 10px rgba(0, 0, 0, 0.1);
    z-index: 90;
    overflow: hidden;
    transition: all 0.3s ease;
}}

.narration-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background-color: var(--primary-color);
    color: white;
}}

.narration-header h3 {{
    margin: 0;
    color: white;
}}

.narration-header button {{
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 1.2rem;
}}

.narration-content {{
    padding: 1rem;
    overflow-y: auto;
    max-height: calc(50vh - 40px);
}}

/* Animations */
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
}}

.fade-in {{
    animation: fadeIn 0.5s ease-in-out;
}}

/* Responsive Design */
@media (max-width: 768px) {{
    .presentation-container {{
        padding: 1rem;
    }}
    
    .controls {{
        bottom: 1rem;
    }}
    
    .narration-panel {{
        width: 100%;
        max-height: 40vh;
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
// Presentation Script
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const slides = document.querySelectorAll('.slide');
    const prevButton = document.getElementById('prev-slide');
    const nextButton = document.getElementById('next-slide');
    const slideCounter = document.getElementById('slide-counter');
    const toggleNarrationButton = document.getElementById('toggle-narration');
    const narrationPanel = document.querySelector('.narration-panel');
    const narrationContent = document.getElementById('narration-content');
    const closeNarrationButton = document.getElementById('close-narration');
    
    // State
    let currentSlide = 0;
    const totalSlides = slides.length;
    const narrations = [];
    
    // Load narrations
    for (let i = 1; i <= totalSlides; i++) {
        fetch(`narration_${i}.txt`)
            .then(response => {
                if (response.ok) {
                    return response.text();
                }
                return `No narration available for slide ${i}`;
            })
            .then(text => {
                narrations[i-1] = text;
            })
            .catch(() => {
                narrations[i-1] = `No narration available for slide ${i}`;
            });
    }
    
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
        slideCounter.textContent = `${index + 1} / ${totalSlides}`;
        
        // Update narration if panel is visible
        if (narrationPanel.style.display !== 'none') {
            narrationContent.textContent = narrations[index] || `Loading narration for slide ${index + 1}...`;
        }
        
        // Update current slide index
        currentSlide = index;
    }
    
    function nextSlide() {
        if (currentSlide < totalSlides - 1) {
            showSlide(currentSlide + 1);
        }
    }
    
    function prevSlide() {
        if (currentSlide > 0) {
            showSlide(currentSlide - 1);
        }
    }
    
    function toggleNarration() {
        if (narrationPanel.style.display === 'none') {
            narrationPanel.style.display = 'block';
            narrationContent.textContent = narrations[currentSlide] || `Loading narration for slide ${currentSlide + 1}...`;
        } else {
            narrationPanel.style.display = 'none';
        }
    }
    
    // Event Listeners
    prevButton.addEventListener('click', prevSlide);
    nextButton.addEventListener('click', nextSlide);
    toggleNarrationButton.addEventListener('click', toggleNarration);
    closeNarrationButton.addEventListener('click', () => {
        narrationPanel.style.display = 'none';
    });
    
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
    
    // Initialize
    showSlide(0);
    narrationPanel.style.display = 'none';
});
"""
        
        return js
