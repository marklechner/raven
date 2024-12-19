# src/processors/deduplication_processor.py
import logging
from typing import List, Dict
from itertools import combinations
import ollama
from models.news_item import NewsItem

logger = logging.getLogger(__name__)

class DeduplicationProcessor:
    def __init__(self, model_name: str = "mistral-small"):
        self.model_name = model_name

    async def _check_similarity(self, item1: NewsItem, item2: NewsItem) -> bool:
        """Check if two news items are covering the same story"""
        prompt = f"""Compare these two news items and determine if they cover the same story.
        Respond with ONLY 'SAME' or 'DIFFERENT'.
        
        Item 1 ({item1.source}):
        Title: {item1.title}
        Date: {item1.published_date}
        Summary: {item1.content[:500]}...
        
        Item 2 ({item2.source}):
        Title: {item2.title}
        Date: {item2.published_date}
        Summary: {item2.content[:500]}...
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            max_tokens=50
        )
        
        return response['response'].strip().upper() == 'SAME'

    async def deduplicate(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items, only comparing between different sources"""
        if not news_items:
            return []

        # Group items by source
        items_by_source: Dict[str, List[NewsItem]] = {}
        for item in news_items:
            if item.source not in items_by_source:
                items_by_source[item.source] = []
            items_by_source[item.source].append(item)

        logger.info(f"Found items from {len(items_by_source)} sources: {', '.join(items_by_source.keys())}")

        # If only one source, return all items
        if len(items_by_source) < 2:
            return news_items

        # Sort items within each source by date
        for source in items_by_source:
            items_by_source[source].sort(key=lambda x: x.published_date, reverse=True)

        # Compare items between different sources
        duplicates = set()  # Track items to remove
        
        # Get all combinations of different sources
        sources = list(items_by_source.keys())
        for source1, source2 in combinations(sources, 2):
            logger.debug(f"Comparing items between {source1} and {source2}")
            
            for item1 in items_by_source[source1]:
                if item1 in duplicates:
                    continue
                    
                for item2 in items_by_source[source2]:
                    if item2 in duplicates:
                        continue
                        
                    try:
                        if await self._check_similarity(item1, item2):
                            # Keep the newer article
                            if item1.published_date >= item2.published_date:
                                duplicates.add(item2)
                                logger.info(
                                    f"Duplicate detected:\n"
                                    f"Keeping: {item1.source} - {item1.title} ({item1.published_date})\n"
                                    f"Dropping: {item2.source} - {item2.title} ({item2.published_date})"
                                )
                            else:
                                duplicates.add(item1)
                                logger.info(
                                    f"Duplicate detected:\n"
                                    f"Keeping: {item2.source} - {item2.title} ({item2.published_date})\n"
                                    f"Dropping: {item1.source} - {item1.title} ({item1.published_date})"
                                )
                            break  # Move to next item1 since we found a duplicate
                    except Exception as e:
                        logger.error(f"Error checking similarity: {str(e)}")
                        continue

        # Create final list of unique items
        unique_items = [item for item in news_items if item not in duplicates]
        
        logger.info(
            f"Deduplication complete: {len(news_items)} items -> {len(unique_items)} unique items "
            f"(removed {len(duplicates)} duplicates)"
        )
        
        return unique_items