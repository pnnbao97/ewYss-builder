"""
Semantic Kernel integration for PDFToSlidesConverter

This module provides the Semantic Kernel integration for the PDF to Academic Slides Converter.
It initializes the kernel, registers services, and creates agents.
"""

import os
import json
from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion
from semantic_kernel.agents import ChatCompletionAgent


class SemanticKernelFactory:
    """
    Factory class for creating and configuring Semantic Kernel instances.
    """
    
    @staticmethod
    def create_kernel(api_key: str) -> Kernel:
        """
        Create and configure a Semantic Kernel instance with Google AI services.
        
        Args:
            api_key: Gemini API key
            
        Returns:
            Configured Semantic Kernel instance
        """
        kernel = Kernel()
        
        # Register Gemini services with different models
        kernel.add_service(GoogleAIChatCompletion(
            gemini_model_id="gemini-2.5-pro-05-06",
            api_key=api_key
        ))
        
        kernel.add_service(GoogleAIChatCompletion(
            gemini_model_id="gemini-2.5-flash-04-17",
            api_key=api_key
        ))
        
        kernel.add_service(GoogleAIChatCompletion(
            gemini_model_id="gemini-2.0-flash",
            api_key=api_key
        ))
        
        return kernel


class AgentFactory:
    """
    Factory class for creating specialized agents using Semantic Kernel.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialize the agent factory with a Semantic Kernel instance.
        
        Args:
            kernel: Configured Semantic Kernel instance
        """
        self.kernel = kernel
        self.prompt_dir = os.path.dirname(os.path.abspath(__file__))
    
    def _load_prompt(self, prompt_path: str) -> str:
        """
        Load a prompt from a file.
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            Prompt content as string
        """
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return ""
    
    def create_orchestrator_agent(self) -> ChatCompletionAgent:
        """
        Create the orchestrator agent.
        
        Returns:
            Orchestrator agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/orchestrator_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert orchestrator for converting PDF documents to academic slides.
        Your task is to coordinate the entire process, delegating tasks to specialized agents
        and combining their results into a cohesive presentation.
        """
        
        return ChatCompletionAgent(
            name="orchestrator",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.5-pro")
        )
    
    def create_content_analyzer_agent(self) -> ChatCompletionAgent:
        """
        Create the content analyzer agent.
        
        Returns:
            Content analyzer agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/content_analyzer_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert content analyzer for academic documents.
        Your task is to analyze PDF content and segment it into logical slides,
        identifying key points, data for visualization, and image needs.
        """
        
        return ChatCompletionAgent(
            name="content_analyzer",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.5-pro")
        )
    
    def create_data_visualization_agent(self) -> ChatCompletionAgent:
        """
        Create the data visualization agent.
        
        Returns:
            Data visualization agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/data_visualization_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert data visualization specialist.
        Your task is to create JavaScript code using Chart.js to visualize data
        in an academic presentation context.
        """
        
        return ChatCompletionAgent(
            name="data_visualization",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.0-flash")
        )
    
    def create_image_search_agent(self) -> ChatCompletionAgent:
        """
        Create the image search agent.
        
        Returns:
            Image search agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/image_search_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert image researcher for academic presentations.
        Your task is to find appropriate images that illustrate academic concepts
        based on keywords and slide content.
        """
        
        return ChatCompletionAgent(
            name="image_search",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.0-flash")
        )
    
    def create_theme_layout_agent(self) -> ChatCompletionAgent:
        """
        Create the theme and layout agent.
        
        Returns:
            Theme and layout agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/theme_layout_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert presentation designer.
        Your task is to select appropriate themes and layouts for academic slides
        based on their content and purpose.
        """
        
        return ChatCompletionAgent(
            name="theme_layout",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.0-flash")
        )
    
    def create_slide_generator_agent(self) -> ChatCompletionAgent:
        """
        Create the slide generator agent.
        
        Returns:
            Slide generator agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/slide_generator_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert HTML/CSS/JS developer specializing in academic presentations.
        Your task is to generate high-quality HTML code for slides with animations,
        responsive design, and professional aesthetics.
        """
        
        return ChatCompletionAgent(
            name="slide_generator",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.5-flash")
        )
    
    def create_narration_agent(self) -> ChatCompletionAgent:
        """
        Create the narration agent.
        
        Returns:
            Narration agent
        """
        prompt_path = os.path.join(self.prompt_dir, "../skills/narration_skill/prompt.txt")
        prompt = self._load_prompt(prompt_path) or """
        You are an expert academic narrator.
        Your task is to create detailed narration scripts for academic slides
        that explain concepts thoroughly and engage the audience.
        """
        
        return ChatCompletionAgent(
            name="narration",
            instructions=prompt,
            service=self.kernel.get_service("gemini-2.5-flash")
        )
