"""
Outer Skies Astrology - Core Prompt Management
This module handles the loading and processing of astrological interpretation prompts.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PromptManager:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.planets_path = self.base_path / "planets"
        self.core_prompts: Dict[str, str] = {}
        self.master_prompt: Optional[str] = None
        self.submission_prompt: Optional[str] = None
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load all core prompts and master chart prompt."""
        try:
            # Load planetary core prompts
            for planet_file in self.planets_path.glob("*_Core.txt"):
                planet_name = planet_file.stem.split("_")[0].upper()
                with open(planet_file, "r", encoding="utf-8") as f:
                    self.core_prompts[planet_name] = f.read()

            # Load master chart prompt
            master_path = self.base_path / "Master_Chart_Prompt.txt"
            if master_path.exists():
                with open(master_path, "r", encoding="utf-8") as f:
                    self.master_prompt = f.read()

            # Load submission prompt
            submission_path = self.base_path / "Chart_Submission_Prompt.txt"
            if submission_path.exists():
                with open(submission_path, "r", encoding="utf-8") as f:
                    self.submission_prompt = f.read()
        except Exception as e:
            logger.error(f"Error loading prompts: {str(e)}")
            raise

    def get_planet_prompt(self, planet: str) -> Optional[str]:
        """Get the core prompt for a specific planet."""
        return self.core_prompts.get(planet.upper())

    def get_master_prompt(self) -> Optional[str]:
        """Get the master chart prompt."""
        return self.master_prompt

    def get_submission_prompt(self) -> Optional[str]:
        """Get the chart submission prompt."""
        return self.submission_prompt

    def format_planet_prompt(self, planet: str, **kwargs) -> Optional[str]:
        """Format a planet's prompt with the provided data."""
        prompt = self.get_planet_prompt(planet)
        if prompt:
            try:
                return prompt.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing required data for {planet}: {e}")
                return None
        return None

    def format_master_prompt(self, **kwargs) -> Optional[str]:
        """Format the master chart prompt with the provided data."""
        if self.master_prompt:
            try:
                return self.master_prompt.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing required data for master prompt: {e}")
                return None
        return None

    def format_submission_prompt(self, **kwargs) -> Optional[str]:
        """Format the submission prompt with the provided data."""
        if self.submission_prompt:
            try:
                return self.submission_prompt.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing required data for submission prompt: {e}")
                return None
        return None

    def get_available_planets(self) -> List[str]:
        """Get list of available planetary prompts."""
        return list(self.core_prompts.keys())

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available AI models."""
        return {
            'gpt-4': {
                'name': 'GPT-4',
                'description': 'Most capable model, best for detailed interpretations',
                'max_tokens': 4000,
                'temperature': 0.7
            },
            'gpt-3.5-turbo': {
                'name': 'GPT-3.5 Turbo',
                'description': 'Fast and efficient, good for quick interpretations',
                'max_tokens': 2000,
                'temperature': 0.7
            },
            'claude-3-opus': {
                'name': 'Claude 3 Opus',
                'description': 'Advanced model with deep understanding of astrology',
                'max_tokens': 4000,
                'temperature': 0.7
            },
            'claude-3-sonnet': {
                'name': 'Claude 3 Sonnet',
                'description': 'Balanced model with good accuracy and speed',
                'max_tokens': 2000,
                'temperature': 0.7
            }
        }


# Create a singleton instance
prompt_manager = PromptManager()
