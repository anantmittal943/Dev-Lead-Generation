from abc import ABC, abstractmethod
from typing import List
from ssp.core.models import Lead

class BaseSource(ABC):
    @abstractmethod
    async def search(self, queries: List[str], fallback_queries: List[str] = None, verbose: bool = False) -> List[Lead]:
        """Search the source and return a list of normalized Lead objects."""
        pass
