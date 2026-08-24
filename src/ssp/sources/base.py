from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ssp.core.models import Candidate

class BaseSource(ABC):
    @abstractmethod
    async def search(self, queries: List[Dict[str, str]], max_age_days: int = 7, verbose: bool = False) -> List[Candidate]:
        """
        Search the source using a list of query dicts [{"query": "...", "event_type": "..."}].
        Return a list of normalized Candidate objects.
        """
        pass
