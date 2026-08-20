from abc import ABC
from typing import List, Dict

class BaseNiche(ABC):
    name: str
    description: str
    
    # Base configuration for scoring
    min_score_threshold: int = 60
    
    reddit_queries: List[str] = []
    hn_queries: List[str] = []
    web_queries: List[str] = []
    
    @classmethod
    def score_candidate(cls, title: str, body: str) -> tuple[int, Dict[str, int]]:
        """Return (total_score, score_breakdown_dict)"""
        return 0, {}
        
    @classmethod
    def get_system_prompt(cls) -> str:
        return ""
