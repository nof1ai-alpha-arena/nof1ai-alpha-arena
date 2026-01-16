"""
Simulated LLM Engine.
Used for generating prediction probabilities based on provided news/events.
"""

import random


class LLMEngine:
    """Simulated LLM engine that 'analyzes' news and returns prediction scores."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def analyze_market(self, news: str):
        """Return a simulated probability based on 'news'."""
        score = random.uniform(0.4, 0.9)
        return {
            "model": self.model_name,
            "news": news,
            "predicted_probability_yes": score,
            "predicted_probability_no": 1 - score,
        }
