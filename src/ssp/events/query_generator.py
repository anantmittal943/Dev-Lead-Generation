import random
from typing import List
from ssp.events.registry import NicheEventConfig

class EventQueryGenerator:
    @staticmethod
    def generate_queries(config: NicheEventConfig) -> List[dict]:
        """
        Generates high-intent queries based on the niche configuration.
        Returns a list of dicts: {"query": str, "event_type": str}
        """
        queries = []
        
        for event in config.events:
            for phrase in event.phrases:
                # Event Phrase + Commercial Context
                comm = random.choice(config.commercial_contexts)
                # Event Phrase + Technical Context
                tech = random.choice(config.technical_contexts)
                
                # Compose variations
                variations = [
                    f'"{phrase}" {comm}',
                    f'"{phrase}" {tech}',
                    f'"{phrase}" {comm} {tech}'
                ]
                
                for var in variations:
                    queries.append({
                        "query": var,
                        "event_type": event.id
                    })
                    
        # Shuffle and enforce query budget
        random.shuffle(queries)
        return queries[:config.max_queries]
