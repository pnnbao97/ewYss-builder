"""
Orchestrator Skill for PDFToSlidesConverter

This module provides functionality to generate the final presentation by combining all slides.
Uses Gemini 2.5 Pro for complex orchestration tasks.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai


class GeneratePresentation:
    """
    Generates the final presentation by combining all slides.
    Uses Gemini 2.5 Pro for complex orchestration tasks.
    """
    
    def __init__(self, model: str, api_key: str):
        """
        Initialize the orchestrator skill with the specified model and API key.
        
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
            I need to generate a complete academic presentation from the provided slides.

            PDF Path: {{pdf_path}}
            Output Directory: {{output_dir}}
            Slides: {{slides}}

            Please generate the final presentation HTML that combines all slides into a cohesive presentation.
            Include navigation controls, transitions, and a consistent theme across all slides.
            """
    
    async def generate_presentation(self, context: Dict[str, str]) -> str:
        """
        Generate the final presentation by combining all slides.
        
        Args:
            context: Dictionary containing PDF path, output directory, and slides
            
        Returns:
            Path to the generated presentation
            
        Raises:
            ValueError: If required data is missing from context
            RuntimeError: If presentation generation fails
        """
        if "pdf_path" not in context:
            raise ValueError("PDF path is missing from context")
        
        if "output_dir" not in context:
            raise ValueError("Output directory is missing from context")
        
        if "slides" not in context:
            raise ValueError("Slides are missing from context")
        
        pdf_path = context["pdf_path"]
        output_dir = context["output_dir"]
        slides = context["slides"]
        
        # Create presentation directory
        presentation_dir = os.path.join(output_dir, "presentation")
        os.makedirs(presentation_dir, exist_ok=True)
        
        try:
            # Parse slides JSON
            slides_data = json.loads(slides)
            
            # Generate index.html with all slides
            index_html = await self._generate_index_html(pdf_path, slides_data)
            
            # Save index.html
            index_path = os.path.join(presentation_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(index_html)
            
            # Generate individual slide files
            for i, slide in enumerate(slides_data):
                slide_html = slide.get("SlideHtml", "")
                slide_path = os.path.join(presentation_dir, f"slide_{i+1}.html")
                with open(slide_path, "w", encoding="utf-8") as f:
                    f.write(slide_html)
                
                # Save narration if available
                narration = slide.get("Narration", "")
                if narration:
                    narration_path = os.path.join(presentation_dir, f"narration_{i+1}.txt")
                    with open(narration_path, "w", encoding="utf-8") as f:
                        f.write(narration)
            
            # Generate CSS and JS files
            await self._generate_assets(presentation_dir)
            
            return f"Presentation generated successfully at {presentation_dir}"
            
        except Exception as e:
            raise RuntimeError(f"Presentation generation failed: {str(e)}")
    
    async def _generate_index_html(self, pdf_path: str, slides_data: List[Dict[str, Any]]) -> str:
        """
        Generate the index.html file that combines all slides.
        
        Args:
            pdf_path: Path to the original PDF
            slides_data: List of slide data
            
        Returns:
            HTML content for index.html
        """
        # Extract PDF filename for the title
        pdf_filename = os.path.basename(pdf_path)
        title = os.path.splitext(pdf_filename)[0]
        
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
        # Generate CSS
        css = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    overflow: hidden;
}

.presentation-container {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    position: relative;
}

.controls {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px;
    background-color: #333;
    color: white;
}

.controls button {
    background: none;
    border: none;
    color: white;
    font-size: 1.2rem;
    cursor: pointer;
    margin: 0 10px;
    padding: 5px 10px;
    border-radius: 4px;
    transition: background-color 0.3s;
}

.controls button:hover {
    background-color: #555;
}

#slide-counter {
    margin: 0 15px;
    font-size: 0.9rem;
}

.slides-container {
    flex: 1;
    overflow: hidden;
    position: relative;
    background-color: white;
}

.slide {
    width: 100%;
    height: 100%;
    padding: 20px;
    box-sizing: border-box;
    overflow: auto;
}

.narration-panel {
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
}

.narration-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    background-color: #f0f0f0;
    border-bottom: 1px solid #ddd;
}

.narration-header h3 {
    margin: 0;
    font-size: 1rem;
}

.narration-header button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
}

.narration-content {
    flex: 1;
    padding: 15px;
    overflow-y: auto;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Slide themes */
.slide-academic {
    background-color: #f0f8ff;
    color: #333;
}

.slide-medical {
    background-color: #f0fff0;
    color: #333;
}

.slide-data {
    background-color: #fff8f0;
    color: #333;
}

/* Common slide elements */
.slide h1 {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
    margin-top: 0;
}

.slide h2 {
    color: #2980b9;
}

.slide ul, .slide ol {
    margin-left: 20px;
}

.slide li {
    margin-bottom: 10px;
}

.slide img {
    max-width: 100%;
    max-height: 60vh;
    display: block;
    margin: 0 auto;
}

.slide .chart-container {
    width: 100%;
    height: 300px;
    margin: 20px 0;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

/* Responsive design */
@media (max-width: 768px) {
    .narration-panel {
        width: 100%;
    }
}
"""
        
        # Generate JS
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
        
        # Save CSS and JS files
        css_path = os.path.join(presentation_dir, "styles.css")
        js_path = os.path.join(presentation_dir, "script.js")
        
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css)
        
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js)
